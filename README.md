
```
# Advanced Blog Platform - Backend (Django)

This is the **backend implementation** of the **Advanced Blog Platform**, built with **Django & Django REST Framework**.  
It provides a scalable, secure, and extensible API for managing blog posts, categories, tags, comments, likes, user profiles, and authentication.  
The backend is designed to power a modern blog system with features such as role-based access, media handling, and API-first development.

---

## 🚀 Features
- **Authentication & Authorization**
  - JWT-based authentication
  - Role-based permissions 
- **Blog Management**
  - Create, read, update, delete (CRUD) blog posts
  - Draft & publish workflows
  - Rich text & media attachments
- **User Profiles**
  - Extended user profile with bio, avatar, and social links
  - Follow/unfollow system
- **Categories & Tags**
  - Organize posts by categories
  - Flexible tagging system
- **Interactions**
  - Commenting system with threaded replies
  - Like & unlike functionality
- **Search & Filtering**
  - Full-text search
  - Filter posts by author, category, tags, or date
- **Scalability Ready**
  - PostgreSQL for production
  - Media storage support (local & cloud-ready)

---

## 🛠 Tech Stack
- **Backend Framework**: Django, Django REST Framework  
- **Database**: SQLite (development), PostgreSQL (production)  
- **Authentication**: JWT (Django REST Framework SimpleJWT)  
- **Other Tools**: Django Admin, Django Filters  


---

## 📝 Development Workflow
```bash
# Clone repository
git clone https://github.com/GordenArcher/blog-system.git
cd blog-system

# Create virtual environment
python -m venv environ
source environ/bin/activate   # For Linux/Mac
environ\Scripts\activate      # For Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
````

---

## 💻 Contribution & Commit Guidelines

* Follow **feature-branch workflow**
* Commit messages should be **clear and descriptive**

  * `feat: add JWT authentication`
  * `fix: resolve comment model bug`
  * `docs: update README`
* Submit pull requests for review

---

## 📜 License

This project is licensed under the **MIT License**.
You are free to use, modify, and distribute this project with attribution.