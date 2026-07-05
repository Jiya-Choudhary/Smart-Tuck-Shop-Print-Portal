# 🏫 Smart Tuck Shop Print Portal
> **A Smart, High-Efficiency Digital Print & Copy Queue System for College Tuckshops.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-green.svg?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite3](https://img.shields.io/badge/SQLite-3-lightblue.svg?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## 📌 Project Overview
During peak hours, college tuckshops experience high congestion due to overlapping class breaks. Students wait in long queues just to print assignments, lab reports, and study sheets, while tuckshop operators struggle to manage pendings files, compute print costs, and reconcile UPI payments.

**Smart Tuck Shop Print Portal** is a web-based client-server application designed to completely digitize campus print queues. It enables students and teachers to upload files remotely, specify printing options, select pickup slots, and track order progress in real-time.

---

## 🎨 System Workflow & UI Architecture

The portal leverages a modern, clean, and responsive **glassmorphic design** optimized for both mobile and desktop screens.

```
       [ Student / Teacher Portal ]       
                   │
                   ▼ (Uploads Files, Specifies Pages & Copies)
       [ Intelligent Sorting Algorithm ] 
                   │
                   ▼ (Groups Orders into priority A, B, C, D)
       [ Live Admin/Operator Console ]    
                   │
                   ▼ (Status updates: Pending ➔ Processing ➔ Completed)
       [ Real-time Order Pickup ]
```

---

## ⚡ The Priority Grouping Logic
To optimize queue turnaround times, the portal implements a dynamic priority sorting algorithm:

$$\text{Urgency Threshold} = \text{Pickup Time} - \text{Current Time} \le 120 \text{ minutes}$$

Based on this threshold and the payment mode, incoming orders are categorized into one of four priority groups:

*   **Group A (Priority 1):** Pre-paid via UPI Online & Urgently needed ($\le 2$ hours).
*   **Group B (Priority 2):** Pay on Pickup & Urgently needed ($\le 2$ hours).
*   **Group C (Priority 3):** Pre-paid via UPI Online & Standard delivery ($> 2$ hours).
*   **Group D (Priority 4):** Pay on Pickup & Standard delivery ($> 2$ hours).

This ensures that critical exam sheets and pre-paid printing orders are always processed first by the operators.

---

## 🖥️ Key Portal Modules

### 🧑‍🎓 Student/Teacher Interface
*   **Drag-&-Drop Document Upload:** Easily upload PDFs, DOCs, or images.
*   **Live Announcement Banner:** Instantly view alerts or status broadcasts posted by the shop administrator.
*   **Instant Queue Tracking:** Search order history and view real-time statuses simply by entering your Roll Number.

### 🛡️ Admin & Operator Control Panel
*   **Bulk Queue Management:** Select multiple print jobs to mark them as *Completed*, *Processing*, or *Cancelled* with a single click.
*   **Dynamic Rates Configuration:** Live update per-page rates for B&W/Color prints and photocopies.
*   **Digital Shop Toggle:** Open or close the portal for submissions with one click (e.g., during tuckshop lunch breaks).
*   **CSV Ledger Export:** Download comprehensive print records and total calculated revenues for accounting logs.

---

## 🗄️ Database Architecture

The application runs on a lightweight, zero-configuration SQLite3 relational model containing two primary tables:

### 1. `orders` Table
Stores details of all submitted print and photocopy requests.

| Column | Data Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record ID |
| `token` | TEXT | - | Formatted queue token (e.g., `A0002`) |
| `name` | TEXT | - | Name of student or instructor |
| `roll_no` | TEXT | - | Student Roll Number for lookup query |
| `pages` | INTEGER | - | Number of pages in target document |
| `copies` | INTEGER | DEFAULT 1 | Total duplicate copies requested |
| `print_type` | TEXT | - | Mode (`Color` / `Black & White`) |
| `pickup_time`| TEXT | - | Set pickup schedule |
| `payment` | TEXT | - | Selected mode: `UPI Online`, `Pay on Pickup` |
| `status` | TEXT | `Pending` | Status: `Pending`, `Processing`, `Completed`, `Cancelled` |
| `task_type` | TEXT | DEFAULT 'Print Out' | Category: `Print Out` or `Photo Copy` |
| `file_path` | TEXT | - | Uploaded document filename |

### 2. `settings` Table
Stores dynamic system-wide configuration keys and operational variables.

| Key | Default Value | Description |
| :--- | :--- | :--- |
| `shop_status` | `open` | Toggles student access to order submission |
| `shop_announcement` | `""` | Broadcasts alerts/notices to the home page |
| `rate_print_bw` | `2.00` | Price per page for B&W printing (INR) |
| `rate_print_color` | `5.00` | Price per page for Color printing (INR) |
| `rate_photo_bw` | `2.00` | Price per page for B&W photocopying (INR) |
| `rate_photo_color`| `5.00` | Price per page for Color photocopying (INR) |

---

## 🚀 Installation & Local Deployment

Get the portal running locally on your campus network in just a few steps:

### 📋 Prerequisites
*   Python 3.8+ installed.

### 💻 Local Run
1.  **Clone or download** this repository.
2.  Navigate to the project root directory:
    ```bash
    cd Smart-Tuck-Shop-Portal
    ```
3.  Set up a virtual environment (Recommended):
    ```bash
    python -m venv venv
    
    # Activate on Windows:
    .\venv\Scripts\activate
    
    # Activate on macOS/Linux:
    source venv/bin/activate
    ```
4.  Install dependencies:
    ```bash
    pip install Flask
    ```
5.  Execute the application script:
    ```bash
    python app.py
    ```
6.  Access the web portals in your browser:
    *   **Student Interface:** `http://127.0.0.1:5000`
    *   **Admin/Operator Panel:** `http://127.0.0.1:5000/admin`

---

## 👥 Project Team & Contributors
This application was developed as a college Summer Training project by:

*   **[Jiya Choudhary]** 
*   **[Ishika Sehgal]** 

*Academic Project — All rights reserved.* 🎓
