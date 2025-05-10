# setup.ps1

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not added to PATH."
    exit 1
}

# Check for Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is not installed or not added to PATH."
    exit 1
}

# Create backend virtual environment if it doesn't exist
if (-not (Test-Path "./venv")) {
    Write-Output "Creating virtual environment..."
    python -m venv venv
} else {
    Write-Output "Virtual environment already exists."
}

# Activate the virtual environment
$activateScript = ".\venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Output "Activating virtual environment..."
    & $activateScript

    # Install requirements if requirements.txt exists
    if (Test-Path "./requirements.txt") {
        Write-Output "Installing backend dependencies from requirements.txt..."
        pip install -r requirements.txt
    } else {
        Write-Output "No requirements.txt found. Skipping backend dependency install."
    }
    
    # Set up Django project
    Write-Output "Setting up Django project..."
    cd backend
    
    # Run migrations
    Write-Output "Running Django migrations..."
    python manage.py makemigrations
    python manage.py migrate
    
    # Create superuser if it doesn't exist
    Write-Output "Would you like to create a superuser? (y/n)"
    $createSuperuser = Read-Host
    if ($createSuperuser -eq "y") {
        python manage.py createsuperuser
    }
    
    cd ..
} else {
    Write-Error "Activation script not found: $activateScript"
}

# Set up frontend
Write-Output "Setting up frontend..."
cd frontend

# Install npm dependencies
if (Test-Path "./package.json") {
    Write-Output "Installing frontend dependencies..."
    npm install
} else {
    Write-Output "Initializing new React project..."
    npx create-react-app .
    
    # Install additional dependencies
    Write-Output "Installing additional frontend dependencies..."
    npm install react-router-dom axios highlight.js styled-components marked
}

cd ..

Write-Output "Setup complete!"
Write-Output ""
Write-Output "To start the backend server:"
Write-Output "  1. Activate the virtual environment: .\venv\Scripts\Activate.ps1"
Write-Output "  2. cd backend"
Write-Output "  3. python manage.py runserver"
Write-Output ""
Write-Output "To start the frontend development server:"
Write-Output "  1. cd frontend"
Write-Output "  2. npm start"
