# RecruitAI Backend

🚀 **AI-Powered Recruitment Platform Backend**

A comprehensive FastAPI backend for an intelligent recruitment platform featuring AI-powered resume analysis, automated candidate matching, video interviews, and advanced analytics.

## ✨ Features

### 🤖 AI-Powered Recruitment
- **Smart Resume Analysis**: Automatic parsing and analysis of PDF, DOC, DOCX resumes
- **Intelligent Matching**: AI-powered candidate-job matching with detailed scoring
- **Video Interviews**: AI-conducted interviews with emotion detection and analysis
- **Automated Screening**: Intelligent candidate qualification and ranking

### 📊 Advanced Analytics
- **Dashboard Metrics**: Comprehensive recruitment analytics and insights
- **Hiring Funnel**: Track conversion rates through the recruitment process
- **Performance Analytics**: Job performance metrics and candidate statistics
- **Time Series Data**: Historical trends and patterns

### 💳 Credit System
- **Usage-Based Billing**: Credit system for AI features
- **Free Tier**: 10 free credits for new users
- **Flexible Pricing**: Pay-per-use model for AI analysis

### 🔐 Enterprise Security
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access**: User and admin role management
- **Data Protection**: Secure file handling and storage
- **API Security**: Rate limiting and input validation

## 🏗️ Architecture

### Tech Stack
- **Framework**: FastAPI 0.104.1
- **Database**: SQLAlchemy with PostgreSQL/SQLite support
- **AI/ML**: OpenAI GPT integration
- **Authentication**: JWT with bcrypt password hashing
- **File Processing**: PyPDF2, python-docx for document parsing
- **Deployment**: Optimized for Render.com

### Project Structure
```
recruitai-backend-complete/
├── app/
│   ├── core/           # Core configuration and database
│   ├── models/         # SQLAlchemy database models
│   ├── routers/        # FastAPI route handlers
│   ├── schemas/        # Pydantic request/response models
│   ├── services/       # Business logic and AI services
│   └── utils/          # Utility functions
├── static/             # Static files
├── uploads/            # File upload directory
├── main.py            # FastAPI application entry point
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- PostgreSQL (for production) or SQLite (for development)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd recruitai-backend-complete
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment setup**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the application**
```bash
# Development
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Key environment variables to configure:

```env
# Required
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost/recruitai

# Optional
DEBUG=False
FREE_CREDITS_ON_SIGNUP=10
RESUME_MATCH_THRESHOLD=0.7
```

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user profile
- `POST /api/auth/refresh` - Refresh access token

### Jobs Management
- `GET /api/jobs/` - List jobs with filtering
- `POST /api/jobs/` - Create new job posting
- `GET /api/jobs/{job_id}` - Get job details
- `PUT /api/jobs/{job_id}` - Update job
- `POST /api/jobs/{job_id}/publish` - Publish job

### Resume Processing
- `POST /api/resumes/upload` - Upload single resume
- `POST /api/resumes/upload-bulk` - Bulk resume upload
- `GET /api/resumes/` - List resumes
- `POST /api/resumes/match` - Match resume to job

### Candidate Management
- `GET /api/candidates/` - List candidates
- `POST /api/candidates/` - Create candidate
- `POST /api/candidates/{id}/schedule-interview` - Schedule interview
- `POST /api/candidates/{id}/hire` - Hire candidate

### AI Interviews
- `POST /api/interviews/` - Create interview
- `POST /api/interviews/start` - Start interview (public)
- `POST /api/interviews/complete` - Complete interview (public)
- `GET /api/interviews/{id}` - Get interview results

### Analytics
- `GET /api/analytics/dashboard` - Dashboard metrics
- `GET /api/analytics/hiring-funnel` - Hiring funnel data
- `GET /api/analytics/time-series` - Time series analytics

### Credits
- `GET /api/credits/balance` - Get credit balance
- `POST /api/credits/purchase` - Purchase credits
- `GET /api/credits/history` - Credit transaction history

## 🔧 Configuration

### AI Features
The platform uses OpenAI's GPT models for:
- Resume parsing and analysis
- Job-candidate matching
- Interview question generation
- Interview response analysis

### Credit Costs
- Resume Analysis: 1 credit
- AI Interview: 3 credits
- AI Matching: 1 credit

### File Upload
- Supported formats: PDF, DOC, DOCX, TXT
- Maximum file size: 10MB
- Automatic virus scanning and validation

## 🚀 Deployment

### Render.com Deployment

1. **Create new Web Service on Render**
2. **Configure build settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Python Version: 3.11

3. **Set environment variables:**
   - Add all required environment variables from `.env.example`
   - Configure `DATABASE_URL` for PostgreSQL

4. **Deploy:**
   - Connect your repository
   - Deploy automatically on push

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Monitoring

### Health Checks
- `GET /health` - Basic health check
- `GET /api/status` - Detailed API status

### Logging
- Structured logging with request tracking
- Error monitoring and alerting
- Performance metrics

## 🔒 Security

### Authentication
- JWT tokens with configurable expiration
- Refresh token rotation
- Password hashing with bcrypt

### Data Protection
- Input validation and sanitization
- File type verification
- SQL injection prevention
- XSS protection

### API Security
- CORS configuration
- Rate limiting
- Request size limits
- Trusted host validation

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## 📈 Performance

### Optimization Features
- Async/await for I/O operations
- Database connection pooling
- Background task processing
- Efficient file handling
- Caching for frequently accessed data

### Scalability
- Horizontal scaling support
- Database optimization
- CDN integration for static files
- Load balancer compatibility

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API documentation at `/docs`

## 🔄 Changelog

### v1.0.0
- Initial release
- Complete AI-powered recruitment platform
- Full API implementation
- Production-ready deployment configuration

---

**Built with ❤️ using FastAPI and OpenAI**

