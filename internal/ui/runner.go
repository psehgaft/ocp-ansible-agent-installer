package ui

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

type Action struct {
	Label        string   `json:"label"`
	Description  string   `json:"description"`
	Role         string   `json:"role"`
	Command      []string `json:"command,omitempty"`
	Playbook     string   `json:"playbook,omitempty"`
	Confirmation string   `json:"confirmation,omitempty"`
}

type Event struct {
	Sequence int       `json:"sequence"`
	Time     time.Time `json:"time"`
	Line     string    `json:"line"`
}

type RunView struct {
	ID         string     `json:"id"`
	Action     string     `json:"action"`
	Profile    string     `json:"profile"`
	Actor      actor      `json:"actor"`
	Status     string     `json:"status"`
	Command    []string   `json:"command"`
	StartedAt  time.Time  `json:"started_at"`
	FinishedAt *time.Time `json:"finished_at,omitempty"`
	ExitCode   *int       `json:"exit_code,omitempty"`
}

type run struct {
	view        RunView
	events      []Event
	subscribers map[chan Event]struct{}
	cancel      context.CancelFunc
}

type Redactor struct {
	mu         sync.RWMutex
	values     []string
	assignment *regexp.Regexp
}

func NewRedactor() *Redactor {
	return &Redactor{assignment: regexp.MustCompile(`(?i)(password|token|secret|authorization)(\s*[=:]\s*)\S+`)}
}

func (redactor *Redactor) Update(payload []byte) {
	var document any
	if json.Unmarshal(payload, &document) != nil {
		return
	}
	values := []string{}
	collectSensitive(document, "", &values)
	sort.Slice(values, func(i, j int) bool { return len(values[i]) > len(values[j]) })
	redactor.mu.Lock()
	redactor.values = values
	redactor.mu.Unlock()
}

func collectSensitive(value any, key string, result *[]string) {
	sensitive := regexp.MustCompile(`(?i)(password|token|secret|private_key|auth_json)`)
	switch typed := value.(type) {
	case map[string]any:
		for childKey, child := range typed {
			collectSensitive(child, childKey, result)
		}
	case []any:
		for _, child := range typed {
			collectSensitive(child, key, result)
		}
	case string:
		if sensitive.MatchString(key) && len(typed) >= 4 {
			*result = append(*result, typed)
		}
	}
}

func (redactor *Redactor) Redact(line string) string {
	redactor.mu.RLock()
	defer redactor.mu.RUnlock()
	for _, value := range redactor.values {
		line = strings.ReplaceAll(line, value, "[REDACTED]")
	}
	return redactor.assignment.ReplaceAllString(line, "$1$2[REDACTED]")
}

type RunManager struct {
	mu             sync.RWMutex
	runs           map[string]*run
	active         string
	repositoryRoot string
	dataRoot       string
	actions        map[string]Action
	redactor       *Redactor
}

func NewRunManager(repositoryRoot, dataRoot string, actions map[string]Action, redactor *Redactor) (*RunManager, error) {
	if err := os.MkdirAll(filepath.Join(dataRoot, "runs"), 0o700); err != nil {
		return nil, err
	}
	manager := &RunManager{runs: map[string]*run{}, repositoryRoot: repositoryRoot, dataRoot: dataRoot, actions: actions, redactor: redactor}
	entries, _ := os.ReadDir(filepath.Join(dataRoot, "runs"))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		content, err := os.ReadFile(filepath.Join(dataRoot, "runs", entry.Name(), "run.json"))
		if err != nil {
			continue
		}
		var view RunView
		if json.Unmarshal(content, &view) != nil {
			continue
		}
		if view.Status == "running" || view.Status == "queued" {
			now, exitCode := time.Now().UTC(), -1
			view.Status, view.FinishedAt, view.ExitCode = "interrupted", &now, &exitCode
		}
		events := []Event{}
		if eventFile, err := os.Open(filepath.Join(dataRoot, "runs", entry.Name(), "events.ndjson")); err == nil {
			scanner := bufio.NewScanner(eventFile)
			for scanner.Scan() {
				var event Event
				if json.Unmarshal(scanner.Bytes(), &event) == nil {
					events = append(events, event)
				}
			}
			_ = eventFile.Close()
		}
		manager.runs[view.ID] = &run{view: view, events: events, subscribers: map[chan Event]struct{}{}}
	}
	return manager, nil
}

func (manager *RunManager) Start(actionName, profile, confirmation string, who actor) (RunView, error) {
	manager.mu.Lock()
	defer manager.mu.Unlock()
	action, ok := manager.actions[actionName]
	if !ok {
		return RunView{}, errors.New("unknown action")
	}
	if !roleAllows(who.Role, action.Role) {
		return RunView{}, errors.New("role is not authorized for this action")
	}
	if action.Confirmation != "" && confirmation != action.Confirmation {
		return RunView{}, fmt.Errorf("confirmation must exactly match %s", action.Confirmation)
	}
	if manager.active != "" {
		return RunView{}, errors.New("another playbook is already running")
	}
	state, err := manager.loadProfile(profile)
	if err != nil {
		return RunView{}, err
	}
	command := manager.actionCommand(action, state)
	id := time.Now().UTC().Format("20060102T150405.000000000Z")
	ctx, cancel := context.WithCancel(context.Background())
	item := &run{view: RunView{ID: id, Action: actionName, Profile: profile, Actor: who, Status: "queued", Command: command, StartedAt: time.Now().UTC()}, subscribers: map[chan Event]struct{}{}, cancel: cancel}
	manager.runs[id] = item
	manager.active = id
	manager.persist(item)
	manager.audit(map[string]any{"time": time.Now().UTC(), "event": "run_started", "run_id": id, "action": actionName, "profile": profile, "actor": who})
	go manager.execute(ctx, item)
	return item.view, nil
}

type profileState struct {
	Inventory         string `json:"inventory"`
	VaultPasswordFile string `json:"vault_password_file"`
}

func (manager *RunManager) loadProfile(profile string) (profileState, error) {
	if !regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$`).MatchString(profile) {
		return profileState{}, errors.New("invalid profile name")
	}
	content, err := os.ReadFile(filepath.Join(manager.dataRoot, "inventories", profile, ".gui-state.json"))
	if err != nil {
		return profileState{}, errors.New("save and validate this profile before running a playbook")
	}
	var state profileState
	if err := json.Unmarshal(content, &state); err != nil {
		return profileState{}, err
	}
	return state, nil
}

func (manager *RunManager) actionCommand(action Action, state profileState) []string {
	if len(action.Command) > 0 {
		result := append([]string{}, action.Command...)
		for index := range result {
			result[index] = strings.ReplaceAll(result[index], "{inventory}", state.Inventory)
		}
		return result
	}
	return []string{"ansible-playbook", "-i", state.Inventory, "--vault-password-file", state.VaultPasswordFile, action.Playbook}
}

func (manager *RunManager) execute(ctx context.Context, item *run) {
	manager.setStatus(item, "running", nil)
	command := exec.CommandContext(ctx, item.view.Command[0], item.view.Command[1:]...)
	command.Dir = manager.repositoryRoot
	command.Env = append(os.Environ(), "PYTHONUNBUFFERED=1", "ANSIBLE_FORCE_COLOR=false")
	pipe, err := command.StdoutPipe()
	if err == nil {
		command.Stderr = command.Stdout
		err = command.Start()
	}
	if err != nil {
		manager.appendEvent(item, err.Error())
		exitCode := 1
		status := "failed"
		if ctx.Err() != nil {
			status = "cancelled"
		}
		manager.finish(item, status, exitCode)
		return
	}
	scanner := bufio.NewScanner(pipe)
	scanner.Buffer(make([]byte, 64*1024), 2*1024*1024)
	for scanner.Scan() {
		manager.appendEvent(item, scanner.Text())
	}
	err = command.Wait()
	exitCode := 0
	status := "succeeded"
	if err != nil {
		status = "failed"
		if ctx.Err() != nil {
			status = "cancelled"
		}
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.ExitCode()
		} else {
			exitCode = 1
		}
	}
	manager.finish(item, status, exitCode)
}

func (manager *RunManager) appendEvent(item *run, line string) {
	manager.mu.Lock()
	event := Event{Sequence: len(item.events) + 1, Time: time.Now().UTC(), Line: manager.redactor.Redact(line)}
	item.events = append(item.events, event)
	for channel := range item.subscribers {
		select {
		case channel <- event:
		default:
		}
	}
	manager.mu.Unlock()
	runDirectory := filepath.Join(manager.dataRoot, "runs", item.view.ID)
	_ = os.MkdirAll(runDirectory, 0o700)
	file, err := os.OpenFile(filepath.Join(runDirectory, "events.ndjson"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err == nil {
		content, _ := json.Marshal(event)
		_, _ = file.Write(append(content, '\n'))
		_ = file.Close()
	}
}

func (manager *RunManager) setStatus(item *run, status string, exitCode *int) {
	manager.mu.Lock()
	item.view.Status = status
	item.view.ExitCode = exitCode
	manager.persist(item)
	manager.mu.Unlock()
}

func (manager *RunManager) finish(item *run, status string, exitCode int) {
	now := time.Now().UTC()
	manager.mu.Lock()
	item.view.Status = status
	item.view.ExitCode = &exitCode
	item.view.FinishedAt = &now
	manager.active = ""
	for channel := range item.subscribers {
		close(channel)
		delete(item.subscribers, channel)
	}
	manager.persist(item)
	manager.mu.Unlock()
	manager.audit(map[string]any{"time": now, "event": "run_finished", "run_id": item.view.ID, "status": status, "exit_code": exitCode, "actor": item.view.Actor})
}

func (manager *RunManager) Cancel(id string, who actor) error {
	manager.mu.Lock()
	item, ok := manager.runs[id]
	if !ok {
		manager.mu.Unlock()
		return errors.New("run not found")
	}
	if !roleAllows(who.Role, "operator") {
		manager.mu.Unlock()
		return errors.New("role is not authorized to cancel runs")
	}
	if item.cancel == nil || (item.view.Status != "running" && item.view.Status != "queued") {
		manager.mu.Unlock()
		return errors.New("run is not active")
	}
	cancel := item.cancel
	manager.mu.Unlock()
	cancel()
	manager.audit(map[string]any{"time": time.Now().UTC(), "event": "run_cancel_requested", "run_id": id, "actor": who})
	return nil
}

func (manager *RunManager) Get(id string) (RunView, []Event, bool) {
	manager.mu.RLock()
	defer manager.mu.RUnlock()
	item, ok := manager.runs[id]
	if !ok {
		return RunView{}, nil, false
	}
	return item.view, append([]Event{}, item.events...), true
}

func (manager *RunManager) List() []RunView {
	manager.mu.RLock()
	defer manager.mu.RUnlock()
	result := make([]RunView, 0, len(manager.runs))
	for _, item := range manager.runs {
		result = append(result, item.view)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].StartedAt.After(result[j].StartedAt) })
	return result
}

func (manager *RunManager) Subscribe(id string) ([]Event, <-chan Event, func(), error) {
	manager.mu.Lock()
	defer manager.mu.Unlock()
	item, ok := manager.runs[id]
	if !ok {
		return nil, nil, nil, errors.New("run not found")
	}
	channel := make(chan Event, 100)
	if item.view.FinishedAt != nil {
		close(channel)
	} else {
		item.subscribers[channel] = struct{}{}
	}
	unsubscribe := func() {
		manager.mu.Lock()
		if _, exists := item.subscribers[channel]; exists {
			delete(item.subscribers, channel)
			close(channel)
		}
		manager.mu.Unlock()
	}
	return append([]Event{}, item.events...), channel, unsubscribe, nil
}

func (manager *RunManager) persist(item *run) {
	runDirectory := filepath.Join(manager.dataRoot, "runs", item.view.ID)
	_ = os.MkdirAll(runDirectory, 0o700)
	_ = writeJSONFile(filepath.Join(runDirectory, "run.json"), item.view, 0o600)
}

func (manager *RunManager) audit(document map[string]any) {
	_ = os.MkdirAll(manager.dataRoot, 0o700)
	file, err := os.OpenFile(filepath.Join(manager.dataRoot, "audit.ndjson"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return
	}
	defer file.Close()
	content, _ := json.Marshal(document)
	_, _ = file.Write(append(content, '\n'))
}
