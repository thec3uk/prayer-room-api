# Prayer Room API - Tech Stack

## Backend

### Framework & Runtime
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.13 | Runtime language |
| Django | 5.1.5 | Web framework |
| Django REST Framework | 0.1.0 | API development |

### Key Django Packages
| Package | Purpose |
|---------|---------|
| django-allauth | Authentication & ChurchSuite OAuth |
| django-cors-headers | CORS handling for API |
| django-import-export | Data import/export |
| django-webhook | Webhook support |
| django-extensions | Development utilities |
| django-htmx | HTMX integration |
| neapolitan | Admin view customization |
| celery | Background task processing |

### Database & Storage
| Technology | Purpose |
|------------|---------|
| PostgreSQL | Production database |
| SQLite | Development database |
| psycopg | PostgreSQL adapter |

### Caching
| Technology | Purpose |
|------------|---------|
| Redis | Cache backend (planned) |

## Frontend

### Technologies
| Technology | Purpose |
|------------|---------|
| HTMX | Dynamic interactions |
| Alpine.js | Lightweight reactivity |
| Vanilla JS | Simple scripting |
| Tailwind CSS | Styling framework |
| Tailwind UI | UI components |

### Separate Frontend (Optional)
| Technology | Purpose |
|------------|---------|
| Remix | React-based frontend app |
| Node.js/npm | Remix runtime |

## API & Integration

### Authentication
| Method | Purpose |
|--------|---------|
| Token Auth | API access (DRF TokenAuthentication) |
| OAuth 2.0 | ChurchSuite single sign-on |

### Integrations
| Service | Purpose |
|---------|---------|
| Zapier | Webhook automation |
| ChurchSuite | Church management system |

## Development Tools

### Package Management
| Tool | Status |
|------|--------|
| Poetry | Current |
| uv | Planned migration |
| pip | Fallback |

### Code Quality
| Tool | Purpose |
|------|---------|
| ruff | Linting & formatting |
| pre-commit | Git hooks |
| django-debug-toolbar | Development debugging |

### Testing
| Tool | Purpose |
|------|---------|
| pytest | Test framework |

## Infrastructure & Deployment

### Hosting
| Component | Technology |
|-----------|------------|
| Server | AWS EC2 |
| PaaS | Dokku |
| Static Files | WhiteNoise |
| WSGI Server | Gunicorn |

### CI/CD
| Tool | Purpose |
|------|---------|
| GitHub Actions | Automated deployment |

### Monitoring & Observability
| Service | Purpose |
|---------|---------|
| Sentry | Error tracking & monitoring |

## Environment Configuration

### Required Environment Variables
```
DATABASE_URL=        # PostgreSQL connection string
SECRET_KEY=          # Django secret key
SENTRY_DSN=          # Sentry error tracking
ALLOWED_HOSTS=       # Allowed host domains
```

### Development Setup
```sh
# Using justfile commands
just init            # Initial setup
just dev             # Run development server
just manage <cmd>    # Django management commands
```

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                         Client Layer                               │
├───────────────────┬─────────────────────┬─────────────────────────┤
│   HTMX/Alpine     │      Remix App      │      External APIs      │
│                   │      (Optional)     │      (Zapier, etc)      │
└─────────┬─────────┴──────────┬──────────┴────────────┬────────────┘
          │                    │                       │
          ▼                    ▼                       ▼
┌───────────────────┐  ┌─────────────────────────────────────────────┐
│   Django Views    │  │              Django REST API                │
│   (Server-side)   │  │            (Token Auth / OAuth)             │
└─────────┬─────────┘  └──────────────────┬──────────────────────────┘
          │                               │
          └───────────────┬───────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │  PostgreSQL │  │   Celery    │  │   Webhooks  │
  │  (Database) │  │  (Tasks)    │  │  (Zapier)   │
  └─────────────┘  └─────────────┘  └─────────────┘
```
