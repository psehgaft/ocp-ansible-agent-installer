package ui

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestAuthenticationAndRoles(t *testing.T) {
	tokens := parseTokens("0123456789abcdef=viewer,abcdef0123456789=admin,short=admin,badbadbadbadbadb=owner")
	if len(tokens) != 2 {
		t.Fatalf("expected two valid tokens, got %d", len(tokens))
	}
	who, ok := authenticate(tokens, "Bearer abcdef0123456789")
	if !ok || who.Role != "admin" {
		t.Fatalf("expected admin authentication, got %#v %v", who, ok)
	}
	if roleAllows("viewer", "operator") || !roleAllows("admin", "operator") {
		t.Fatal("role hierarchy is incorrect")
	}
}

func TestNonLoopbackRequiresAuthentication(t *testing.T) {
	t.Setenv("INSTALLER_UI_LISTEN", "0.0.0.0:8080")
	t.Setenv("INSTALLER_UI_AUTH_TOKENS", "")
	if _, err := ConfigFromEnvironment(); err == nil {
		t.Fatal("expected public listener without tokens to fail")
	}
}

func TestRedactorRemovesSubmittedAndAssignmentSecrets(t *testing.T) {
	redactor := NewRedactor()
	redactor.Update([]byte(`{"secrets":{"vault_git_token":"top-secret-value"}}`))
	line := redactor.Redact("token=another-secret value=top-secret-value")
	if line != "token=[REDACTED] value=[REDACTED]" {
		t.Fatalf("unexpected redaction: %s", line)
	}
}

func TestRunManagerRejectsMissingConfirmationAndRestoresHistory(t *testing.T) {
	root := t.TempDir()
	data := filepath.Join(root, "data")
	profile := filepath.Join(data, "inventories", "demo")
	if err := os.MkdirAll(profile, 0o700); err != nil {
		t.Fatal(err)
	}
	state := profileState{Inventory: "/tmp/inventory.yml", VaultPasswordFile: "/tmp/vault-pass"}
	if err := writeJSONFile(filepath.Join(profile, ".gui-state.json"), state, 0o600); err != nil {
		t.Fatal(err)
	}
	actions := map[string]Action{"impact": {Role: "admin", Command: []string{"/bin/sh", "-c", "printf 'completed\\n'"}, Confirmation: "RUN"}}
	manager, err := NewRunManager(root, data, actions, NewRedactor())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := manager.Start("impact", "demo", "wrong", actor{Role: "admin"}); err == nil {
		t.Fatal("expected confirmation failure")
	}
	view, err := manager.Start("impact", "demo", "RUN", actor{Name: "test", Role: "admin"})
	if err != nil {
		t.Fatal(err)
	}
	for range 100 {
		current, _, _ := manager.Get(view.ID)
		if current.FinishedAt != nil {
			break
		}
		// A short poll avoids adding synchronization hooks to production code.
		<-timeAfter()
	}
	current, events, _ := manager.Get(view.ID)
	if current.Status != "succeeded" || len(events) != 1 || events[0].Line != "completed" {
		t.Fatalf("unexpected run: %#v %#v", current, events)
	}
	restored, err := NewRunManager(root, data, actions, NewRedactor())
	if err != nil {
		t.Fatal(err)
	}
	_, restoredEvents, ok := restored.Get(view.ID)
	if !ok || len(restoredEvents) != 1 {
		t.Fatal("persisted run history was not restored")
	}
}

func TestRunManagerPreventsConcurrentRunsAndSupportsCancellation(t *testing.T) {
	root := t.TempDir()
	data := filepath.Join(root, "data")
	profile := filepath.Join(data, "inventories", "demo")
	if err := os.MkdirAll(profile, 0o700); err != nil {
		t.Fatal(err)
	}
	state := profileState{Inventory: "/tmp/inventory.yml", VaultPasswordFile: "/tmp/vault-pass"}
	if err := writeJSONFile(filepath.Join(profile, ".gui-state.json"), state, 0o600); err != nil {
		t.Fatal(err)
	}
	actions := map[string]Action{"slow": {Role: "operator", Command: []string{"/bin/sleep", "5"}}}
	manager, err := NewRunManager(root, data, actions, NewRedactor())
	if err != nil {
		t.Fatal(err)
	}
	view, err := manager.Start("slow", "demo", "", actor{Name: "test", Role: "operator"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := manager.Start("slow", "demo", "", actor{Name: "test", Role: "operator"}); err == nil {
		t.Fatal("expected concurrent run rejection")
	}
	if err := manager.Cancel(view.ID, actor{Name: "test", Role: "operator"}); err != nil {
		t.Fatal(err)
	}
	for range 100 {
		current, _, _ := manager.Get(view.ID)
		if current.FinishedAt != nil {
			if current.Status != "cancelled" {
				t.Fatalf("expected cancelled status, got %s", current.Status)
			}
			return
		}
		<-timeAfter()
	}
	t.Fatal("cancelled run did not finish")
}

func TestServerRequiresBearerTokenAndServesRepositorySchema(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(source), "..", ".."))
	config := Config{
		ListenAddress:  "127.0.0.1:0",
		RepositoryRoot: root,
		DataRoot:       t.TempDir(),
		PythonBinary:   "python3",
		AuthTokens:     map[string]string{"0123456789abcdef": "viewer"},
	}
	server, err := NewServer(config)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodGet, "/api/schema", nil)
	response := httptest.NewRecorder()
	server.httpServer.Handler.ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", response.Code)
	}

	request = httptest.NewRequest(http.MethodGet, "/api/schema", nil)
	request.Header.Set("Authorization", "Bearer 0123456789abcdef")
	response = httptest.NewRecorder()
	server.httpServer.Handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", response.Code, response.Body.String())
	}
	if !strings.Contains(response.Header().Get("Content-Security-Policy"), "default-src 'self'") {
		t.Fatal("security headers are missing")
	}
	var schema struct {
		Operators []json.RawMessage `json:"operators"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &schema); err != nil || len(schema.Operators) < 52 {
		t.Fatalf("unexpected schema response: %v, operators=%d", err, len(schema.Operators))
	}
}

func timeAfter() <-chan time.Time { return time.After(10 * time.Millisecond) }
