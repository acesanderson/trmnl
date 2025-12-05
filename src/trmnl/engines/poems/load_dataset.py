import kagglehub

# Download latest version
path = kagglehub.dataset_download("tgdivy/poetry-foundation-poems")

print("Path to dataset files:", path)
