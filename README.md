<div align="center">

# 🧪 BookLab-System
### *Advanced Laboratory Reservation & Management Ecosystem*

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg?style=for-the-badge)](#)



**BookLab** is a robust, production-ready web application designed to streamline the scheduling and management of university laboratory resources. Built for the academic environment, it ensures fair access, secure authentication, and administrative oversight.

[🌐 Live Demo](#) | [📚 Documentation](#) | [🐞 Report Bug](#)

</div>

---

## 📖 Project Overview

Managing laboratory hours and equipment manually is prone to errors and scheduling conflicts. **BookLab** provides a centralized platform where students can request slots, and administrators can monitor usage in real-time. The system features a multi-tiered approval process, ensuring that only verified and authorized students can utilize sensitive lab environments.

---

## ✨ Key Features

### 🔐 Advanced Authentication & Security
- **Passive-to-Active Workflow:** New students are registered as "Passive." Access is only granted after **Email Verification** and manual **Admin Approval**.
- **Secure Password Reset:** Fully integrated SMTP-based password recovery system.
- **Session Management:** Secure handling of user sessions and verification codes.

### 📅 Reservation Management
- **Smart Booking:** Prevent double-booking and schedule overlaps.
- **Dynamic Status Tracking:** Track lab availability and equipment status in real-time.
- **User Dashboard:** Students can view, edit, or cancel their upcoming reservations.

### 🛠 Administrative Control (AdminLTE Integrated)
- **Unified Command Center:** Manage Users, Labs, and Appointments from a modern, responsive dashboard.
- **One-Click Approval:** Bulk-approve students and toggle account status (`is_active`).
- **Audit Logs:** Track system activity for security and accountability.

---

## 🚀 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.13, Django 5.x |
| **Frontend** | Bootstrap 5, AdminLTE 3, Custom CSS3 |
| **Database** | SQLite (Development), PostgreSQL (Production) |
| **Security** | Python-Decouple (Env Var Management), Django Signals |
| **Mailing** | Google SMTP (TLS/SSL) |
| **DevOps** | Git, PythonAnywhere Deployment |

---

## 📸 Screenshots

<div align="center">
  <img src="https://via.placeholder.com/400x250?text=Login+Screen+Preview" width="45%" alt="Login Screen"/>
  <img src="https://via.placeholder.com/400x250?text=Admin+Dashboard+Preview" width="45%" alt="Dashboard"/>
</div>

---

## 🛠 Installation & Setup

### Prerequisites
- Python 3.13+
- Virtualenv

### Step-by-Step Guide

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/yourusername/BookLab-System.git](https://github.com/yourusername/BookLab-System.git)
   cd BookLab-System
