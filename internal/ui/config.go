package ui

import (
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	ListenAddress  string
	RepositoryRoot string
	DataRoot       string
	PythonBinary   string
	AuthTokens     map[string]string
}

func ConfigFromEnvironment() (Config, error) {
	repositoryRoot := envOrDefault("INSTALLER_UI_REPOSITORY_ROOT", ".")
	repositoryRoot, err := filepath.Abs(repositoryRoot)
	if err != nil {
		return Config{}, err
	}
	dataRoot := envOrDefault("INSTALLER_UI_DATA_ROOT", filepath.Join(repositoryRoot, "artifacts", "gui"))
	dataRoot, err = filepath.Abs(dataRoot)
	if err != nil {
		return Config{}, err
	}
	config := Config{
		ListenAddress:  envOrDefault("INSTALLER_UI_LISTEN", "127.0.0.1:8080"),
		RepositoryRoot: repositoryRoot,
		DataRoot:       dataRoot,
		PythonBinary:   envOrDefault("INSTALLER_UI_PYTHON", "python3"),
		AuthTokens:     parseTokens(os.Getenv("INSTALLER_UI_AUTH_TOKENS")),
	}
	if len(config.AuthTokens) == 0 && !isLoopbackListen(config.ListenAddress) {
		return Config{}, errors.New("INSTALLER_UI_AUTH_TOKENS is required when listening outside loopback")
	}
	return config, nil
}

func envOrDefault(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}

func parseTokens(raw string) map[string]string {
	result := map[string]string{}
	for _, entry := range strings.Split(raw, ",") {
		parts := strings.SplitN(strings.TrimSpace(entry), "=", 2)
		if len(parts) != 2 || !validRole(parts[1]) || len(parts[0]) < 16 {
			continue
		}
		result[parts[0]] = parts[1]
	}
	return result
}

func isLoopbackListen(address string) bool {
	host, _, err := net.SplitHostPort(address)
	if err != nil {
		return false
	}
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

type actor struct {
	Name string `json:"name"`
	Role string `json:"role"`
}

func validRole(role string) bool {
	return role == "viewer" || role == "operator" || role == "admin"
}

func roleAllows(actual, required string) bool {
	ranks := map[string]int{"viewer": 1, "operator": 2, "admin": 3}
	return ranks[actual] >= ranks[required]
}

func authenticate(tokens map[string]string, authorization string) (actor, bool) {
	if len(tokens) == 0 {
		return actor{Name: "local", Role: "admin"}, true
	}
	provided := strings.TrimSpace(strings.TrimPrefix(authorization, "Bearer "))
	for token, role := range tokens {
		if len(token) == len(provided) && subtle.ConstantTimeCompare([]byte(token), []byte(provided)) == 1 {
			return actor{Name: fmt.Sprintf("%s-%x", role, token[:4]), Role: role}, true
		}
	}
	return actor{}, false
}

func writeJSONFile(path string, value any, mode os.FileMode) error {
	content, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(content, '\n'), mode)
}
