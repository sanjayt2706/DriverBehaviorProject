# Run from D:\MajorProject\DriverBehaviorProject
# Scaffolds empty folders matching Architecture.md / FolderStructure.md

$dirs = @(
  # Android — Layers 1-2
  "Android\app\src\main\java\com\driverisk\app\data\local\entity"
  "Android\app\src\main\java\com\driverisk\app\data\local\dao"
  "Android\app\src\main\java\com\driverisk\app\data\remote\dto"
  "Android\app\src\main\java\com\driverisk\app\data\repository"
  "Android\app\src\main\java\com\driverisk\app\sensors"
  "Android\app\src\main\java\com\driverisk\app\service"
  "Android\app\src\main\java\com\driverisk\app\ui\home"
  "Android\app\src\main\java\com\driverisk\app\ui\recording"
  "Android\app\src\main\java\com\driverisk\app\ui\history"
  "Android\app\src\main\java\com\driverisk\app\ui\result"
  "Android\app\src\main\java\com\driverisk\app\ui\map"
  "Android\app\src\main\java\com\driverisk\app\util"

  # Backend — Layers 3-7
  "Backend\app\api\routes"
  "Backend\app\schemas"
  "Backend\app\models"
  "Backend\app\crud"
  "Backend\app\processing"
  "Backend\app\ml"
  "Backend\app\explain"
  "Backend\app\utils"
  "Backend\ml_model"
  "Backend\tests"

  # ML — Pipeline A (offline training)
  "ML\src"
  "ML\notebooks"
  "ML\outputs"

  # Dashboard — Layer 8
  "Dashboard\pages"

  # Dataset
  "Dataset\raw"
  "Dataset\processed"

  # Documentation
  "Documentation"

  # Papers
  "Papers"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

Write-Host "Folder structure created." -ForegroundColor Green
