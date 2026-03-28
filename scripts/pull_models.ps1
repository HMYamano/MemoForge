$ErrorActionPreference = "Stop"

$reasoningModel = if ($env:REASONING_MODEL) { $env:REASONING_MODEL } else { "qwen3:30b" }
$visionModel = if ($env:VISION_MODEL) { $env:VISION_MODEL } else { "gemma3:27b" }
$embeddingModel = if ($env:EMBEDDING_MODEL) { $env:EMBEDDING_MODEL } else { "embeddinggemma" }

Write-Host "Pulling $reasoningModel ..."
docker compose exec ollama ollama pull $reasoningModel

Write-Host "Pulling $visionModel ..."
docker compose exec ollama ollama pull $visionModel

Write-Host "Pulling $embeddingModel ..."
try {
    docker compose exec ollama ollama pull $embeddingModel
} catch {
    Write-Warning "Could not pull $embeddingModel. Continuing."
}

Write-Host "Done."
