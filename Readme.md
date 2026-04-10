# 🏫 SGSITS Timetable Generator

A complete timetable generation system for engineering colleges with role-based access (Admin, Teacher, Student).

## 🚀 Features

- **Multi-role Authentication**: Admin, Teacher, and Student dashboards
- **Automatic Timetable Generation**: Uses intelligent scheduling algorithm
- **Teacher Conflict Prevention**: No teacher assigned to multiple classes at same time
- **Room Management**: Track room capacity and availability
- **Course Management**: Add subjects, assign teachers, create sections
- **Excel Export**: Download timetables as Excel files
- **Beautiful UI**: Space-themed modern interface with animations
- **SQLite Database**: Lightweight, no separate database server needed

## 📁 Tech Stack

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS
- Vite
- Axios
- React Router DOM
- Lucide Icons
- SheetJS (Excel export)

**Backend:**
- FastAPI (Python)
- SQLite3
- JWT Authentication
- CORS enabled

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/jeorgeiiii/Time-Table-Generator.git
cd Time-Table-Generator

# Install Python dependencies
pip install fastapi uvicorn pyjwt python-multipart

# Initialize database
python reset_db.py

# Run backend server
python backend_api.py