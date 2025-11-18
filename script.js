let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
    setupEventListeners();
});

function setupEventListeners() {
    // Login
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    
    // Logout
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    
    // Student tabs
    document.getElementById('my-courses-btn')?.addEventListener('click', () => {
        showSection('my-courses-section');
        setActiveTab('my-courses-btn');
    });
    
    document.getElementById('all-courses-btn')?.addEventListener('click', () => {
        showSection('all-courses-section');
        setActiveTab('all-courses-btn');
        loadAllCourses();
    });
}

// Authentication
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/current-user');
        const data = await response.json();
        
        if (data.logged_in) {
            currentUser = data.user;
            showDashboard();
        } else {
            showLogin();
        }
    } catch (error) {
        console.error('Error checking login status:', error);
        showLogin();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('login-error');
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });
        
        // Try to parse JSON response; if parsing fails, data will be null
        let data = null;
        try {
            data = await response.json();
        } catch (e) {
            console.warn('Failed to parse JSON response from /api/login', e);
        }

        if (response.ok && data && data.success) {
            currentUser = data.user;
            errorDiv.textContent = '';
            showDashboard();
        } else {
            // Prefer server-provided error message when available
            let msg = 'Invalid username or password';
            if (data && data.error) {
                msg = data.error;
            } else if (!response.ok) {
                msg = data && data.error ? data.error : `Server error (${response.status})`;
            }
            errorDiv.textContent = msg;
        }
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = 'An error occurred. Please try again.';
    }
}

async function handleLogout() {
    try {
        await fetch('/api/logout', {
            method: 'POST',
        });
        
        currentUser = null;
        showLogin();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Page Navigation
function showLogin() {
    document.getElementById('login-page').classList.add('active');
    document.getElementById('dashboard-page').classList.remove('active');
}

function showDashboard() {
    document.getElementById('login-page').classList.remove('active');
    document.getElementById('dashboard-page').classList.add('active');
    
    document.getElementById('welcome-text').textContent = `Welcome ${currentUser.full_name}!`;
    
    // Show appropriate view based on role
    document.getElementById('student-view').classList.remove('active');
    document.getElementById('teacher-view').classList.remove('active');
    document.getElementById('admin-view').classList.remove('active');
    
    if (currentUser.role === 'student') {
        document.getElementById('student-view').classList.add('active');
        loadMyCourses();
    } else if (currentUser.role === 'teacher') {
        document.getElementById('teacher-view').classList.add('active');
        loadTeacherCourses();
    } else if (currentUser.role === 'admin') {
        document.getElementById('admin-view').classList.add('active');
    }
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

function setActiveTab(btnId) {
    document.querySelectorAll('.btn-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(btnId).classList.add('active');
}

// Student Functions
async function loadMyCourses() {
    try {
        const response = await fetch('/api/my-courses');
        const courses = await response.json();
        
        const tbody = document.getElementById('my-courses-body');
        tbody.innerHTML = '';
        
        if (courses.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">No courses enrolled yet. Click "Add Courses" to enroll!</td></tr>';
            return;
        }
        
        courses.forEach(course => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${course.name}</td>
                <td>${course.teacher}</td>
                <td>${course.time}</td>
                <td>${course.enrolled}/${course.capacity}</td>
                <td>${course.grade}</td>
                <td><button class="btn btn-danger" onclick="unenrollFromCourse(${course.id})">Unenroll</button></td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading courses:', error);
    }
}

async function unenrollFromCourse(courseId) {
    if (!confirm('Are you sure you want to unenroll from this course?')) return;

    try {
        const response = await fetch('/api/unenroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_id: courseId })
        });

        const data = await response.json().catch(() => ({}));

        if (response.ok && data.success) {
            // Refresh both lists so UI stays in sync
            loadMyCourses();
            loadAllCourses();
        } else {
            alert(data.error || data.message || 'Failed to unenroll');
        }
    } catch (err) {
        console.error('Error unenrolling:', err);
        alert('An error occurred while unenrolling.');
    }
}

async function loadAllCourses() {
    try {
        const [allCoursesRes, myCoursesRes] = await Promise.all([
            fetch('/api/courses'),
            fetch('/api/my-courses')
        ]);
        
        const allCourses = await allCoursesRes.json();
        const myCourses = await myCoursesRes.json();
        
        const myCoursesIds = new Set(myCourses.map(c => c.id));
        
        const tbody = document.getElementById('all-courses-body');
        tbody.innerHTML = '';
        
        allCourses.forEach(course => {
            const row = document.createElement('tr');
            const isEnrolled = myCoursesIds.has(course.id);
            const isFull = course.enrolled >= course.capacity;
            
            row.innerHTML = `
                <td>${course.name}</td>
                <td>${course.teacher}</td>
                <td>${course.time}</td>
                <td>${course.enrolled}/${course.capacity}</td>
                <td>
                    ${isEnrolled 
                        ? '<span style="color: #27ae60; font-weight: 600;">Enrolled</span>' 
                        : isFull
                            ? '<button class="btn btn-success" disabled>Full</button>'
                            : `<button class="btn btn-success" onclick="enrollInCourse(${course.id})">Enroll</button>`
                    }
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading all courses:', error);
    }
}

async function enrollInCourse(courseId) {
    try {
        const response = await fetch('/api/enroll', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ course_id: courseId }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadAllCourses();
            loadMyCourses();
        } else {
            alert(data.error || 'Failed to enroll in course');
        }
    } catch (error) {
        console.error('Error enrolling:', error);
        alert('An error occurred while enrolling');
    }
}

// Teacher Functions
async function loadTeacherCourses() {
    try {
        const response = await fetch('/api/my-courses');
        const courses = await response.json();
        
        const container = document.getElementById('teacher-courses-list');
        container.innerHTML = '';
        
        for (const course of courses) {
            const courseCard = document.createElement('div');
            courseCard.className = 'course-card';
            
            courseCard.innerHTML = `
                <h3>${course.name}</h3>
                <div class="course-info">
                    <div><strong>Time:</strong> ${course.time}</div>
                    <div><strong>Enrolled:</strong> ${course.enrolled}/${course.capacity}</div>
                </div>
                <div class="students-list">
                    <h4>Students:</h4>
                    <div id="students-${course.id}">Loading...</div>
                </div>
            `;
            
            container.appendChild(courseCard);
            
            loadCourseStudents(course.id);
        }
    } catch (error) {
        console.error('Error loading teacher courses:', error);
    }
}

async function loadCourseStudents(courseId) {
    try {
        const response = await fetch(`/api/course/${courseId}/students`);
        const students = await response.json();
        
        const studentsDiv = document.getElementById(`students-${courseId}`);
        studentsDiv.innerHTML = '';
        
        if (students.length === 0) {
            studentsDiv.innerHTML = '<p style="color: #999; padding: 20px 0;">No students enrolled yet</p>';
            return;
        }
        
        students.forEach(student => {
            const studentItem = document.createElement('div');
            studentItem.className = 'student-item';
            
            studentItem.innerHTML = `
                <div class="student-name">${student.student_name}</div>
                <div class="grade-input-group">
                    <label>Grade:</label>
                    <input type="number" 
                           min="0" 
                           max="100" 
                           value="${student.grade}" 
                           id="grade-${student.enrollment_id}">
                    <button class="btn btn-success" 
                            onclick="updateGrade(${student.enrollment_id})">
                        Save
                    </button>
                </div>
            `;
            
            studentsDiv.appendChild(studentItem);
        });
    } catch (error) {
        console.error('Error loading students:', error);
    }
}

async function updateGrade(enrollmentId) {
    const input = document.getElementById(`grade-${enrollmentId}`);
    const grade = parseInt(input.value);
    
    if (isNaN(grade) || grade < 0 || grade > 100) {
        alert('Please enter a valid grade between 0 and 100');
        return;
    }
    
    try {
        const response = await fetch(`/api/enrollment/${enrollmentId}/grade`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ grade }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            input.style.borderColor = '#27ae60';
            setTimeout(() => {
                input.style.borderColor = '';
            }, 1000);
        } else {
            alert('Failed to update grade');
        }
    } catch (error) {
        console.error('Error updating grade:', error);
        alert('An error occurred while updating grade');
    }
}