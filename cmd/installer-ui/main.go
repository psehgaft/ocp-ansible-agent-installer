package main

import (
	"log"
	"os"

	"github.com/psehgaft/ocp-ansible-agent-installer/gui/internal/ui"
)

func main() {
	config, err := ui.ConfigFromEnvironment()
	if err != nil {
		log.Fatal(err)
	}
	server, err := ui.NewServer(config)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("OpenShift Installer UI listening on %s", config.ListenAddress)
	if err := server.ListenAndServe(); err != nil {
		log.Printf("server stopped: %v", err)
		os.Exit(1)
	}
}
