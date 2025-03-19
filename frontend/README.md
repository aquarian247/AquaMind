# AquaMind Frontend

This is the frontend application for AquaMind, an aquaculture management system built with Vue.js 3 and Tailwind CSS.

## Technology Stack

- **Vue.js 3**: Core framework using the Composition API
- **Vue Router**: For navigation and routing
- **Pinia**: State management
- **Axios**: API communication
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Vite**: Build tool and development server

## Project Structure

```
frontend/
├── public/               # Static assets
├── src/
│   ├── assets/           # Images and styles
│   │   ├── styles/
│   │   └── images/
│   ├── components/       # Reusable Vue components
│   │   ├── common/
│   │   ├── infrastructure/
│   │   ├── batch/
│   │   └── environmental/
│   ├── composables/      # Shared composition functions
│   ├── router/           # Vue Router configuration
│   ├── store/            # Pinia stores
│   ├── views/            # Page components
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── infrastructure/
│   │   └── batch/
│   ├── App.vue           # Root component
│   └── main.js           # Application entry point
├── index.html            # HTML entry point
├── package.json          # Project configuration
└── vite.config.js        # Vite configuration
```

## Setup and Development

### Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

### Installation

1. Install dependencies:

```bash
npm install
```

### Running the Development Server

Start the development server:

```bash
npm run dev
```

This will start the Vite development server, typically on http://localhost:5173.

### Building for Production

Build the application for production:

```bash
npm run build
```

This will generate optimized assets in the `dist` directory.

## Authentication

This frontend is designed to work with the Django backend's authentication system using JWT tokens. Authentication status is managed through the Pinia store in `src/store/auth.js`.

## API Communication

API requests are handled through a custom composable function in `src/composables/useApi.js` which provides a wrapper around Axios for simplified API communication including:

- Automatic token handling
- Error handling
- Response formatting

## Integration with Django Backend

The frontend expects the Django backend to be running at `http://localhost:8000` by default. This can be configured in the `vite.config.js` file.

The API proxy is configured to forward all `/api` requests to the Django backend.
