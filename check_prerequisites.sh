#!/bin/bash

# === Configuration ===
OLLAMA_URL="http://localhost:11434"
MODEL_NAME="llama3.2:3b"        # Change to llama3.2:1b or others if needed
MIN_DISK_SPACE_GB=6             # ~6 GB minimum for 3b
MIN_RAM_GB=4                    # Minimum RAM

# === Couleurs terminal ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === Fonction affichage status ===
print_status() {
    if [ "$1" -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        [ -n "$3" ] && echo -e "${YELLOW}  $3${NC}"
        exit 1
    fi
}

# === 1. Vérifie qu’Ollama est installé ===
echo "🔍 Checking if Ollama is installed..."
if command -v ollama >/dev/null 2>&1; then
    OLLAMA_VERSION=$(ollama --version)
    print_status 0 "Ollama is installed (version: $OLLAMA_VERSION)"
else
    print_status 1 "Ollama is not installed" "Install from https://ollama.com/download"
fi

# === 2. Démarre le serveur Ollama en arrière-plan ===
echo "🚀 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# === 3. Attend qu’il soit prêt ===
echo "⏳ Waiting for Ollama server to become ready..."
for i in {1..15}; do
    if curl -s -f "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        print_status 0 "Ollama server is running"
        break
    else
        sleep 1
    fi
done

if ! curl -s -f "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    print_status 1 "Ollama server did not start in time" "Try again manually with 'ollama serve'"
fi

# === 4. Vérifie que le modèle est dispo, sinon pull ===
echo "📦 Checking model: $MODEL_NAME"
if ollama list | grep -q "$MODEL_NAME"; then
    print_status 0 "Model $MODEL_NAME already present"
else
    echo "⬇️ Pulling model $MODEL_NAME..."
    if ollama pull "$MODEL_NAME"; then
        print_status 0 "Model $MODEL_NAME pulled successfully"
    else
        print_status 1 "Failed to pull model $MODEL_NAME" "Check internet or model name"
    fi
fi

# === 5. Vérifie l’espace disque dispo ===
echo "💽 Checking disk space..."
DISK_AVAILABLE=$(df -k / | tail -1 | awk '{ print int($4 / 1024 / 1024) }')  # en GB
if [ "$DISK_AVAILABLE" -ge "$MIN_DISK_SPACE_GB" ]; then
    print_status 0 "Sufficient disk space (${DISK_AVAILABLE} GB available)"
else
    print_status 1 "Insufficient disk space (${DISK_AVAILABLE} GB)" "Minimum $MIN_DISK_SPACE_GB GB required"
fi

# === 6. Vérifie la RAM dispo ===
echo "🧠 Checking available RAM..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux: use 'free'
    FREE_RAM=$(free -g | awk '/Mem:/ { print $7 }')
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: use 'vm_stat'
    PAGES_FREE=$(vm_stat | grep "Pages free" | awk '{gsub(/\./,"",$3); print $3}')
    PAGES_SPEC=$(vm_stat | grep "Pages speculative" | awk '{gsub(/\./,"",$3); print $3}')
    PAGE_SIZE=$(sysctl -n hw.pagesize)

    if [[ -n "$PAGES_FREE" && -n "$PAGES_SPEC" && -n "$PAGE_SIZE" ]]; then
        FREE_RAM_BYTES=$(( (PAGES_FREE + PAGES_SPEC) * PAGE_SIZE ))
        FREE_RAM=$(( FREE_RAM_BYTES / 1024 / 1024 / 1024 ))
    else
        print_status 1 "Unable to determine RAM on macOS" "Check 'vm_stat' and 'sysctl' output"
    fi
else
    print_status 1 "Unsupported OS for RAM check" "Only Linux and macOS supported"
fi

if [ "$FREE_RAM" -ge "$MIN_RAM_GB" ]; then
    print_status 0 "Sufficient RAM (${FREE_RAM} GB available)"
else
    print_status 1 "Insufficient RAM (${FREE_RAM} GB available, need ${MIN_RAM_GB} GB)" "Close other apps or add more memory"
fi


# === 7. Vérifie la connectivité réseau ===
echo "🌐 Checking network to Ollama registry..."
if curl -s -f https://registry.ollama.ai/v2/ >/dev/null; then
    print_status 0 "Network access to Ollama registry is OK"
else
    print_status 1 "No connectivity to Ollama registry" "Check internet or use VPN"
fi

# === Tout est OK ===
echo -e "${GREEN}✅ All checks passed. Ollama is ready to serve.${NC}"

# === Garde le processus attaché ===
wait $OLLAMA_PID
