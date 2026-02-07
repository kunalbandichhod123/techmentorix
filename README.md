# TechMentorX
TechMentorX is a healthcare-oriented web application focused on delivering a structured, secure, and user-friendly interface for managing health-related dashboards, authentication, and personalized features.

This repository contains the frontend (UI/UX) implementation of the project.

---

## Overview

The application is designed with modular components and a scalable structure to support healthcare use cases such as doctor dashboards, protected routes, and user-specific data visualization.

---

## Features

- User authentication interface
- Doctor dashboard
- Protected routing
- Meal plan visualization components
- Modular and reusable UI components
- Clean and maintainable code structure

---

## Technology Stack

- Frontend Framework: React.js
- Styling: CSS
- Routing: React Router
- Authentication Handling: Service-based architecture
- Version Control: Git and GitHub

---

## Project Structure

```text
src/
├── components/
│   ├── MealPlanTable.js
│   ├── MealPlanPlanViewer.js
│   ├── MyHealthPlan.js
│   └── ProtectedRoute.js
├── pages/
│   ├── Login.js
│   └── DoctorDashboard.js
├── services/
│   └── authService.js
├── styles/
│   ├── dashboard.css
│   └── login.css
├── App.js
├── App.css
└── index.js
