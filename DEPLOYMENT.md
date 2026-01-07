# Balans AI Web - Render.com Deployment Guide

## Prerequisites

- GitHub repository configured
- Render.com account created
- Database accessible from Render's servers

## Deployment Steps

### 1. Push Code to GitHub

Make sure all changes are committed and pushed to your GitHub repository:

```bash
git add .
git commit -m "feat: Add Render deployment configuration"
git push origin main
```

### 2. Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" button
3. Select "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and configure the service

### 3. Configure Environment Variables

Set the following environment variables in Render Dashboard:

**Required:**
- `DB_HOST` - Your MySQL database host (146.103.126.207)
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name (BalansAiBot)
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token

**Auto-generated:**
- `SECRET_KEY` - Will be generated automatically by Render

**Optional (already set in render.yaml):**
- `DB_PORT` - Database port (default: 3306)
- `DEBUG` - Set to False for production
- `OTP_EXPIRY_MINUTES` - OTP expiration time (default: 5)
- `OTP_LENGTH` - OTP code length (default: 6)
- `TELEGRAM_BOT_USERNAME` - Bot username (default: BalansAiBot)

### 4. Database Configuration

**Important:** Ensure your MySQL database:
- Allows connections from Render's IP addresses
- Has proper tables created (use database.py schema)
- Has firewall rules configured for external access

### 5. Deploy

After configuration:
1. Click "Apply" to create the service
2. Render will automatically:
   - Install dependencies
   - Run build.sh
   - Start the application with Gunicorn
3. Monitor the deployment logs for any errors

### 6. Post-Deployment Verification

1. Check the service URL provided by Render
2. Verify the health check endpoint: `https://your-app.onrender.com/api/config`
3. Test login functionality
4. Monitor application logs for errors

## Application URLs

After deployment, your application will be available at:
- Main app: `https://balansai-web.onrender.com/`
- Login: `https://balansai-web.onrender.com/login`
- API config: `https://balansai-web.onrender.com/api/config`

## Troubleshooting

### Database Connection Issues
- Verify database credentials in environment variables
- Check if database allows remote connections
- Verify firewall rules allow Render's IP addresses

### Build Failures
- Check build logs in Render dashboard
- Verify all dependencies in requirements.txt
- Ensure build.sh has execute permissions

### Application Crashes
- Check application logs in Render dashboard
- Verify environment variables are set correctly
- Check database connectivity
- Review Gunicorn worker configuration

### Session Issues
- Ensure SECRET_KEY is set and consistent
- Check if cookies are being set correctly
- Verify HTTPS is being used

## Performance Optimization

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- 750 hours/month of runtime
- Consider upgrading for production use

### Scaling Options
If you need better performance:
1. Upgrade to paid plan for always-on service
2. Increase worker count in Procfile/render.yaml
3. Consider using a CDN for static assets
4. Optimize database queries

## Monitoring

Monitor your application:
1. Render Dashboard - Service logs and metrics
2. Database monitoring - Query performance
3. Telegram bot - Error notifications
4. Custom logging - Application-level logs

## Updates and Maintenance

To deploy updates:
1. Push changes to GitHub
2. Render will automatically detect and redeploy
3. Or manually trigger redeploy from Render dashboard

## Security Checklist

- [x] DEBUG set to False in production
- [x] SECRET_KEY auto-generated and secure
- [x] Database credentials stored as environment variables
- [x] Telegram bot token secured
- [ ] HTTPS enforced (automatic on Render)
- [ ] Database has proper access controls
- [ ] Regular security updates applied

## Support

For issues:
- Render Documentation: https://render.com/docs
- Balans AI Support: GitHub Issues
- Database Support: Contact your database provider

## Backup Strategy

Recommended backups:
1. Database backups (daily recommended)
2. Environment variable documentation
3. Code versioned in Git
4. Configuration files backed up

---

**Last Updated:** 2026-01-07
**Version:** 1.0.0
