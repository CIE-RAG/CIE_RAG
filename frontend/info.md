## Info Doc on UI

### Overview

This zip file contains the setup for a React project with Vite, Tailwind CSS, Typescript and proper configuration files for linting and development.

### Project Dependencies

_note : these dependencies are already a part of the zip file and are mentioned in `package.json`_

**1. Runtime Dependencies**

<pre>"dependencies": {
  "lucide-react": "^0.344.0",     // Icon library for React
  "react": "^18.3.1",             // React core library
  "react-dom": "^18.3.1"          // React DOM rendering library
}</pre>

**2. Development Dependencies**

<pre>
"devDependencies": {
  "@eslint/js": "^9.9.1",                     // ESLint config for JS
  "@types/react": "^18.3.5",                  // TypeScript types for React
  "@types/react-dom": "^18.3.0",              // TypeScript types for ReactDOM
  "@vitejs/plugin-react": "^4.3.1",           // Vite plugin for React
  "autoprefixer": "^10.4.18",                 // PostCSS plugin to add vendor prefixes
  "eslint": "^9.9.1",                         // JavaScript/TypeScript linter
  "eslint-plugin-react-hooks": "^5.1.0-rc.0", // ESLint rules for React hooks
  "eslint-plugin-react-refresh": "^0.4.11",   // ESLint plugin for HMR
  "globals": "^15.9.0",                       // Global variable definitions for ESLint
  "postcss": "^8.4.35",                       // Tool for transforming CSS
  "tailwindcss": "^3.4.1",                    // Utility-first CSS framework
  "typescript": "^5.5.3",                     // TypeScript compiler
  "typescript-eslint": "^8.3.0",              // TypeScript plugin for ESLint
  "vite": "^5.4.2"                            // Frontend build tool
}
</pre>

### Key Directories and Files

#### `/public` Directory

- Contains static assets, in this case the CIE Logo and the PES Logo.

#### `/src` Directory

- `main.tsx` Entry point that renders the App component into the DOM
- `App.tsx` Root component containing the main application logic
- `index.css` Global styles, Tailwind CSS imports and custom CSS
- `vite-env.d.ts` TypeScript declarations for Vite-specific features
- `components/` Reusable UI components used across the application

#### Configuration Files

- `vite.config.ts` Vite build tool configuration
- `tsconfig.json` TypeScript compiler options
- `tailwind.config.js` Tailwind CSS customization
- `postcss.config.js` PostCSS plugins configuration
- `eslint.config.js` Code linting rules

#### Package Management

- `package.json` Project Dependencies and Scripts
- `package-lock.json` Locked dependency versions for consistency

#### Other Root Files

- `.gitignore` Specifies files and folders to ignore in Git
- `index.html` Single HTML file used by Vite to inject the React App
- `info.md` Markdown file containing Documentation
- `tsconfig.app.json`, `tsconfig.node.json` Separate TS configs for app and node-specific logic

### Prerequisites

Before executing this application ensure you have :

- **Node.js** (v18 or higher)
- **npm**(v7 or higher) or **yarn**(v1.22 or higher) package manager

### Version Compatibility

This project uses :

- React 18.3.1
- Typescript 5.5.3
- Vite 5.4.2
- Tailwind CSS 3.4.1

### Installation and Running

**1. Install Dependencies**

<pre>npm install
<i>or</i>
yarn install</pre>

**2. Run in Development Mode**

<pre>npm run dev
<i>or</i>
yarn dev</pre>

_This should typically start the server at `http://localhost:5173`_

### Technology Stack

- **React** : UI Library
- **Typescript** : Type-safe JavaScript superset
- **Vite** : Fast build tool and development server
- **Tailwind CSS** : Utility-first CSS framework
- **PostCSS** : CSS post-processor
- **ESLint** : Code linting and formatting
