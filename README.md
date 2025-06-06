# AquaMind: Aquaculture Management System

AquaMind is a comprehensive aquaculture management platform designed to optimize operations, monitor environmental conditions, and manage fish stocks across the entire aquaculture lifecycle. The system integrates real-time environmental monitoring, resource management, and operational planning to enhance productivity and sustainability in aquaculture operations.

## 🌊 Features

AquaMind provides a robust set of features organized around key functional areas:

- **Environmental Monitoring**: Track water quality, temperature, oxygen levels, and other critical parameters using TimescaleDB for efficient time-series data storage
- **Infrastructure Management**: Manage physical assets, stations, and containers with detailed tracking and maintenance scheduling
- **Batch Management**: Monitor fish batches throughout their lifecycle from broodstock to harvest
- **Inventory Management**: Track feed, medications, and other resources with detailed usage reporting
- **Medical Records**: Maintain comprehensive health records, treatments, and vaccination schedules
- **Operational Planning**: Optimize daily operations with task scheduling and resource allocation
- **Data Visualization**: Interactive dashboards providing insights into key performance metrics
- **Role-Based Access Control**: Secure access based on organizational structure including geographies, subsidiaries, and functional areas

## 🛠️ Technology Stack

AquaMind is built using modern technologies for reliability, scalability, and maintainability:

- **Backend**: Django 4.2.11 (Python 3.11)
- **Database**: PostgreSQL with TimescaleDB extension for efficient time-series data management
- **API**: Django REST Framework for robust API development
- **Frontend**: TBD
- **Authentication**: Django's authentication system with role-based access control
- **Testing**: Django's testing framework for comprehensive test coverage

## 🏗️ Architecture

The application follows Django's Model-Template-View (MTV) architecture with these key components:

1. **Core Apps**:
   - `core`: Shared functionality and utilities
   - `users`: Authentication and role-based access control
   - `infrastructure`: Physical assets, stations, and containers management
   - `batch`: Fish batch lifecycle management
   - `environmental`: Monitoring systems integration and time-series data
   - `operational`: Daily optimization and planning
   - `inventory`: Resource and feed management
   - `medical`: Health tracking and veterinary records

2. **Data Storage**:
   - PostgreSQL with TimescaleDB extension for efficient time-series data storage
   - Hypertables for environmental readings and weather data

3. **Security**:
   - Role-based access control reflecting the organizational structure
   - Multiple access levels across geographies (Faroe Islands, Scotland)
   - Access control for subsidiaries (Broodstock, Freshwater, Farming, Logistics)
   - Functional access for horizontals (QA, Finance, Veterinarians)

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose (recommended)
- Alternatively: Python 3.11, PostgreSQL with TimescaleDB extension, and Node.js with npm

### Installation

#### Option 1: Using Docker (Recommended)

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/AquaMind.git
cd AquaMind
```

2. **Start the development environment with Docker Compose**

```bash
docker-compose up -d
```

3. **Apply migrations**

```bash
docker-compose exec web python manage.py migrate
```

4. **Create a superuser**

```bash
docker-compose exec web python manage.py createsuperuser
```

5. **Access the application**

- Django backend: http://localhost:8000

For more details on the Docker environment, see [Docker Development Environment](docs/docker_environment.md).

#### Option 2: Manual Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/AquaMind.git
cd AquaMind
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up the database**

Ensure PostgreSQL with TimescaleDB extension is installed and running, then create the database:

```bash
createdb aquamind
```

5. **Apply migrations**

```bash
python manage.py migrate
```

6. **Create a superuser**

```bash
python manage.py createsuperuser
```

7. **Run the development server**

```bash
python manage.py runserver
```

## 📁 Project Structure

```
AquaMind/
├── .devcontainer/          # VS Code Dev Container configuration
├── apps/                   # Application modules
│   ├── core/               # Core functionality and utilities
│   ├── users/              # User authentication and permissions
│   ├── infrastructure/     # Physical assets management
│   ├── batch/              # Fish batch lifecycle management
│   ├── environmental/      # Environmental monitoring
│   ├── operational/        # Daily operations and planning
│   ├── inventory/          # Resource and feed management
│   └── medical/            # Health tracking and records
├── aquamind/               # Project settings
│   ├── settings.py         # Django settings
│   ├── urls.py             # Main URL configuration
│   └── wsgi.py             # WSGI configuration
├── docs/                   # Documentation
│   ├── prd.md              # Product Requirements Document
│   ├── data model.md       # Database schema documentation
│   └── docker_environment.md # Docker setup documentation
├── frontend/               # Vue.js 3 frontend
├── Dockerfile.dev          # Development Dockerfile
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
└── manage.py               # Django management script
```

## 🧪 Testing

Run the test suite with:

```bash
python manage.py test
```

## 📚 Development Guidelines

- Follow PEP 8 style guide for Python code
- Document all functions and classes with docstrings following PEP 257
- Use flake8 for linting Python code
- Use Django's testing framework for unit and integration tests
- Follow Django's security best practices
- Optimize database queries with select_related and prefetch_related
- When working with TimescaleDB tables, ensure time-based partitioning columns are included in primary keys or unique constraints

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
