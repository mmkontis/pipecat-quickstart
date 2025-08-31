# 🚀 Pipecat Bot - Sevalla Deployment Guide

This guide explains how to deploy your Pipecat voice AI bot to Sevalla with multiple process support for handling concurrent conversations.

## 📁 Project Structure

```
pp1/
├── bot.py                    # Main bot logic
├── production.py             # Production ASGI app
├── runner.py                 # Custom runner (alternative)
├── Dockerfile                # Docker configuration
├── requirements.txt          # Python dependencies
├── gunicorn.conf.py          # Gunicorn configuration
├── sevalla.yml              # Sevalla deployment config
├── start.sh                  # Production startup script
├── templates/                # HTML templates
└── .dockerignore            # Docker ignore file
```

## 🔧 Local Testing

### Single Process (Development)
```bash
# Start single bot process
python bot.py
```

### Multiple Processes (Production Test)
```bash
# Start with 2 worker processes
gunicorn -w 2 -k uvicorn.workers.UvicornWorker production:app --bind 0.0.0.0:7860

# Or use the production script
./start.sh
```

### Test Multiple Connections
```bash
# Open multiple browser tabs to http://localhost:7860
# Each tab = isolated conversation
```

## ☁️ Sevalla Deployment

### 1. Prepare Environment Variables

In your Sevalla dashboard, set these secrets:

```bash
DEEPGRAM_API_KEY=your_deepgram_key
OPENAI_API_KEY=your_openai_key
CARTESIA_API_KEY=your_cartesia_key
```

### 2. Deploy to Sevalla

```bash
# Upload your project files to Sevalla
# The sevalla.yml will handle the deployment configuration
```

### 3. Configure Domain (Optional)

Point your domain to your Sevalla deployment:
- **Root URL**: `https://your-domain.com/` → `/client`
- **Health Check**: `https://your-domain.com/health`

## ⚙️ Configuration Options

### Scaling Workers

**For Low Traffic (1-5 concurrent users):**
```yaml
# sevalla.yml
resources:
  cpu: "1"
  memory: "2GB"

environment:
  - name: WORKERS
    value: "2"
```

**For Medium Traffic (6-20 concurrent users):**
```yaml
resources:
  cpu: "2"
  memory: "4GB"

environment:
  - name: WORKERS
    value: "4"
```

**For High Traffic (20+ concurrent users):**
```yaml
resources:
  cpu: "4"
  memory: "8GB"

scaling:
  max_instances: 5

environment:
  - name: WORKERS
    value: "8"
```

### Environment Variables

```bash
# Production optimizations
PYTHONUNBUFFERED=1          # Immediate log output
PYTHONPATH=/app            # Python path
WORKERS=4                  # Gunicorn workers per instance

# Optional performance tuning
GUNICORN_TIMEOUT=300       # WebRTC connection timeout
GUNICORN_KEEPALIVE=30      # Keep-alive timeout
```

## 🔍 Monitoring & Debugging

### Health Checks

Your deployment includes automatic health checks:
- **Endpoint**: `/health`
- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Start Period**: 60 seconds (allows startup time)

### Logs

Monitor your application logs in Sevalla dashboard:
- **Application Logs**: General app output
- **Access Logs**: HTTP requests
- **Error Logs**: Exceptions and errors

### Common Issues

#### High Memory Usage
```yaml
# Increase memory allocation
resources:
  memory: "6GB"
```

#### Slow Response Times
```yaml
# Add more CPU cores
resources:
  cpu: "4"
```

#### Too Many Connections
```yaml
# Enable auto-scaling
scaling:
  max_instances: 10
  target_cpu_utilization: 70
```

## 🧪 Testing Your Deployment

### 1. Basic Connectivity
```bash
curl https://your-sevalla-domain.com/health
# Should return: {"status":"healthy"}
```

### 2. WebRTC Client
```bash
open https://your-sevalla-domain.com/client
# Should load the voice chat interface
```

### 3. API Endpoints
```bash
curl -X POST https://your-sevalla-domain.com/api/offer \
  -H "Content-Type: application/json" \
  -d '{"type": "offer", "sdp": "test"}'
```

## 📊 Performance Metrics

### Expected Performance

| Configuration | Concurrent Users | CPU | Memory |
|---------------|------------------|-----|--------|
| 1 CPU, 2GB RAM | 2-5 users | ~60% | ~1.5GB |
| 2 CPU, 4GB RAM | 5-15 users | ~70% | ~3GB |
| 4 CPU, 8GB RAM | 15-30 users | ~75% | ~6GB |

### Monitoring Commands

```bash
# Check active connections
curl https://your-sevalla-domain.com/health

# Monitor resource usage in Sevalla dashboard
# - CPU utilization
# - Memory usage
# - Request count
# - Response times
```

## 🔐 Security Considerations

### API Keys
- ✅ Store API keys as Sevalla secrets
- ✅ Never commit keys to version control
- ✅ Rotate keys regularly

### Network Security
- ✅ Use HTTPS (Sevalla provides SSL)
- ✅ Configure proper CORS if needed
- ✅ Monitor for unusual traffic patterns

### Data Privacy
- ✅ Conversations are isolated per connection
- ✅ No persistent storage by default
- ✅ Consider GDPR compliance for user data

## 🚀 Production Checklist

- [ ] API keys configured in Sevalla secrets
- [ ] Domain configured (optional)
- [ ] Resource allocation set appropriately
- [ ] Health checks passing
- [ ] WebRTC client loading
- [ ] Multiple concurrent connections tested
- [ ] Monitoring alerts configured
- [ ] Backup strategy in place

## 🆘 Troubleshooting

### Deployment Issues

**Build Failures:**
```bash
# Check Docker build logs in Sevalla
# Verify all dependencies in requirements.txt
# Check .dockerignore for unnecessary files
```

**Runtime Errors:**
```bash
# Check application logs in Sevalla dashboard
# Verify environment variables are set
# Check API keys are valid
```

**Performance Issues:**
```bash
# Monitor CPU/memory usage
# Adjust worker count
# Consider horizontal scaling
```

### WebRTC Issues

**Connection Problems:**
- Check browser console for WebRTC errors
- Verify microphone permissions
- Test with different browsers

**Audio Quality Issues:**
- Check network connectivity
- Verify API keys for speech services
- Monitor service quotas

## 📞 Support

For Sevalla-specific issues:
- Check Sevalla documentation
- Contact Sevalla support

For Pipecat-specific issues:
- Check Pipecat documentation
- GitHub issues: https://github.com/pipecat-ai/pipecat

---

## 🎯 Quick Start Commands

```bash
# Local testing
python bot.py

# Production testing
./start.sh

# Deploy to Sevalla
# Upload project files to Sevalla dashboard
```

Your Pipecat bot is now production-ready for Sevalla! 🚀
