package ui

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

//go:embed web/*
var webAssets embed.FS

type contextKey string

const actorKey contextKey = "actor"

type Server struct {
	config     Config
	schema     json.RawMessage
	actions    map[string]Action
	runs       *RunManager
	redactor   *Redactor
	httpServer *http.Server
}

func NewServer(config Config) (*Server, error) {
	command := exec.Command(config.PythonBinary, filepath.Join(config.RepositoryRoot, "scripts", "gui_config.py"), "schema", "--root", config.RepositoryRoot)
	content, err := command.Output()
	if err != nil {
		return nil, fmt.Errorf("load GUI schema: %w", err)
	}
	var envelope struct {
		Actions map[string]Action `json:"actions"`
	}
	if err := json.Unmarshal(content, &envelope); err != nil {
		return nil, err
	}
	redactor := NewRedactor()
	runs, err := NewRunManager(config.RepositoryRoot, config.DataRoot, envelope.Actions, redactor)
	if err != nil {
		return nil, err
	}
	server := &Server{config: config, schema: content, actions: envelope.Actions, runs: runs, redactor: redactor}
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", server.health)
	mux.HandleFunc("/api/schema", server.requireRole("viewer", server.getSchema))
	mux.HandleFunc("/api/config/validate", server.requireRole("viewer", server.validateConfig))
	mux.HandleFunc("/api/config/save", server.requireRole("operator", server.saveConfig))
	mux.HandleFunc("/api/runs", server.requireRole("viewer", server.runsCollection))
	mux.HandleFunc("/api/runs/", server.requireRole("viewer", server.runResource))
	mux.HandleFunc("/api/audit", server.requireRole("admin", server.audit))
	webRoot, _ := fs.Sub(webAssets, "web")
	mux.Handle("/", http.FileServer(http.FS(webRoot)))
	server.httpServer = &http.Server{Addr: config.ListenAddress, Handler: securityHeaders(mux), ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 0, IdleTimeout: 60 * time.Second}
	return server, nil
}

func (server *Server) ListenAndServe() error { return server.httpServer.ListenAndServe() }

func securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		response.Header().Set("X-Content-Type-Options", "nosniff")
		response.Header().Set("X-Frame-Options", "DENY")
		response.Header().Set("Referrer-Policy", "no-referrer")
		response.Header().Set("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'")
		next.ServeHTTP(response, request)
	})
}

func (server *Server) requireRole(role string, handler http.HandlerFunc) http.HandlerFunc {
	return func(response http.ResponseWriter, request *http.Request) {
		who, ok := authenticate(server.config.AuthTokens, request.Header.Get("Authorization"))
		if !ok {
			writeError(response, http.StatusUnauthorized, "authentication required")
			return
		}
		if !roleAllows(who.Role, role) {
			writeError(response, http.StatusForbidden, "role is not authorized")
			return
		}
		handler(response, request.WithContext(context.WithValue(request.Context(), actorKey, who)))
	}
}

func (server *Server) health(response http.ResponseWriter, _ *http.Request) {
	writeJSON(response, http.StatusOK, map[string]string{"status": "ok"})
}

func (server *Server) getSchema(response http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	response.Header().Set("Content-Type", "application/json")
	_, _ = response.Write(server.schema)
}

func (server *Server) helper(response http.ResponseWriter, request *http.Request, operation string) {
	body, err := io.ReadAll(http.MaxBytesReader(response, request.Body, 4<<20))
	if err != nil {
		writeError(response, http.StatusBadRequest, "invalid request body")
		return
	}
	arguments := []string{filepath.Join(server.config.RepositoryRoot, "scripts", "gui_config.py"), operation, "--root", server.config.RepositoryRoot, "--data-root", server.config.DataRoot}
	command := exec.CommandContext(request.Context(), server.config.PythonBinary, arguments...)
	command.Stdin = strings.NewReader(string(body))
	output, err := command.CombinedOutput()
	if operation == "save" && json.Valid(output) {
		var result struct {
			Valid bool `json:"valid"`
		}
		if json.Unmarshal(output, &result) == nil && result.Valid {
			server.redactor.Update(body)
		}
	}
	status := http.StatusOK
	if err != nil {
		status = http.StatusUnprocessableEntity
	}
	if !json.Valid(output) {
		writeError(response, http.StatusInternalServerError, "configuration helper failed")
		return
	}
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(status)
	_, _ = response.Write(output)
}

func (server *Server) validateConfig(response http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodPost {
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	server.helper(response, request, "validate")
}

func (server *Server) saveConfig(response http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodPost {
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	server.helper(response, request, "save")
}

func (server *Server) audit(response http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	content, err := os.ReadFile(filepath.Join(server.config.DataRoot, "audit.ndjson"))
	if err != nil && !os.IsNotExist(err) {
		writeError(response, http.StatusInternalServerError, "cannot read audit history")
		return
	}
	items := []json.RawMessage{}
	for _, line := range strings.Split(strings.TrimSpace(string(content)), "\n") {
		if json.Valid([]byte(line)) {
			items = append(items, json.RawMessage(line))
		}
	}
	if len(items) > 500 {
		items = items[len(items)-500:]
	}
	writeJSON(response, http.StatusOK, map[string]any{"events": items})
}

func (server *Server) runsCollection(response http.ResponseWriter, request *http.Request) {
	switch request.Method {
	case http.MethodGet:
		writeJSON(response, http.StatusOK, map[string]any{"runs": server.runs.List()})
	case http.MethodPost:
		var input struct {
			Action       string `json:"action"`
			Profile      string `json:"profile"`
			Confirmation string `json:"confirmation"`
		}
		if err := decodeJSON(response, request, &input); err != nil {
			return
		}
		who := request.Context().Value(actorKey).(actor)
		view, err := server.runs.Start(input.Action, input.Profile, input.Confirmation, who)
		if err != nil {
			writeError(response, http.StatusConflict, err.Error())
			return
		}
		writeJSON(response, http.StatusAccepted, view)
	default:
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (server *Server) runResource(response http.ResponseWriter, request *http.Request) {
	path := strings.TrimPrefix(request.URL.Path, "/api/runs/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		writeError(response, http.StatusNotFound, "run not found")
		return
	}
	id := parts[0]
	if len(parts) == 2 && parts[1] == "events" && request.Method == http.MethodGet {
		server.streamEvents(response, request, id)
		return
	}
	if len(parts) == 2 && parts[1] == "cancel" && request.Method == http.MethodPost {
		who := request.Context().Value(actorKey).(actor)
		if err := server.runs.Cancel(id, who); err != nil {
			writeError(response, http.StatusConflict, err.Error())
			return
		}
		writeJSON(response, http.StatusAccepted, map[string]string{"status": "cancellation_requested"})
		return
	}
	if len(parts) != 1 || request.Method != http.MethodGet {
		writeError(response, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	view, events, ok := server.runs.Get(id)
	if !ok {
		writeError(response, http.StatusNotFound, "run not found")
		return
	}
	writeJSON(response, http.StatusOK, map[string]any{"run": view, "events": events})
}

func (server *Server) streamEvents(response http.ResponseWriter, request *http.Request, id string) {
	flusher, ok := response.(http.Flusher)
	if !ok {
		writeError(response, http.StatusInternalServerError, "streaming is unavailable")
		return
	}
	history, channel, unsubscribe, err := server.runs.Subscribe(id)
	if err != nil {
		writeError(response, http.StatusNotFound, err.Error())
		return
	}
	defer unsubscribe()
	response.Header().Set("Content-Type", "text/event-stream")
	response.Header().Set("Cache-Control", "no-cache")
	response.Header().Set("X-Accel-Buffering", "no")
	writeEvent := func(event Event) {
		content, _ := json.Marshal(event)
		_, _ = fmt.Fprintf(response, "data: %s\n\n", content)
		flusher.Flush()
	}
	for _, event := range history {
		writeEvent(event)
	}
	for {
		select {
		case event, open := <-channel:
			if !open {
				return
			}
			writeEvent(event)
		case <-request.Context().Done():
			return
		}
	}
}

func decodeJSON(response http.ResponseWriter, request *http.Request, target any) error {
	decoder := json.NewDecoder(http.MaxBytesReader(response, request.Body, 4<<20))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		writeError(response, http.StatusBadRequest, "invalid JSON request")
		return err
	}
	return nil
}

func writeJSON(response http.ResponseWriter, status int, value any) {
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(status)
	_ = json.NewEncoder(response).Encode(value)
}

func writeError(response http.ResponseWriter, status int, message string) {
	writeJSON(response, status, map[string]string{"error": message})
}
