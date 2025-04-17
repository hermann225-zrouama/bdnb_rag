#!/bin/bash
# Check if the llama3.2:3b model is already present
if ! ollama list | grep -q "llama3.2"; then
    echo "Pulling llama3.2:3b model..."
    ollama pull llama3.2
else
    echo "llama3.2 model already exists."
fi

# Start the Ollama server
exec ollama serve