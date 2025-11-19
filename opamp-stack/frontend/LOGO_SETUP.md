# 🎨 Logo and Favicon Setup Guide

## 📍 Where to Place Your Images

### For Favicons and Static Assets
Place in: **`/home/alexandre/Documentos/github/AmpBridge/opamp-stack/frontend/public/`**

```
frontend/public/
├── favicon.ico           # Multi-size ICO (16x16, 32x32, 48x48)
├── favicon-16x16.png    # 16x16 PNG favicon
├── favicon-32x32.png    # 32x32 PNG favicon
├── apple-touch-icon.png # 180x180 PNG for iOS/Apple devices
├── logo.svg             # Primary SVG logo (scalable)
└── logo.png             # PNG logo fallback (512x512 recommended)
```

### For Logo Assets Used in Code
Place in: **`/home/alexandre/Documentos/github/AmpBridge/opamp-stack/frontend/src/assets/`**

```
frontend/src/assets/
├── logo.svg             # If you want to import in components
├── logo-dark.svg        # Dark theme variant (optional)
└── logo-light.svg       # Light theme variant (optional)
```

---

## 🎯 Quick Setup Steps

### Step 1: Generate Your Favicon Pack
Use a favicon generator to create all required sizes:
- **Recommended tool**: https://realfavicongenerator.net/
- Upload your logo (preferably 512x512 PNG or SVG)
- Download the generated favicon pack

### Step 2: Copy Files
```bash
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack/frontend/public/

# Copy your generated files here:
# - favicon.ico
# - favicon-16x16.png
# - favicon-32x32.png
# - apple-touch-icon.png
# - logo.svg
# - logo.png
```

### Step 3: Rebuild Frontend
```bash
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack
docker compose build frontend
docker compose up -d frontend
```

---

## 📝 File Requirements

### favicon.ico
- **Sizes**: Contains 16x16, 32x32, and 48x48
- **Format**: ICO
- **Used by**: Older browsers, bookmarks

### favicon-16x16.png
- **Size**: 16x16 pixels
- **Format**: PNG with transparency
- **Used by**: Browser tabs

### favicon-32x32.png
- **Size**: 32x32 pixels
- **Format**: PNG with transparency
- **Used by**: Browser tabs on high-DPI displays

### apple-touch-icon.png
- **Size**: 180x180 pixels
- **Format**: PNG
- **Used by**: iOS home screen icons, Safari bookmarks

### logo.svg
- **Size**: Scalable (viewBox recommended)
- **Format**: SVG
- **Used by**: Modern browsers, header logo
- **Design**: Should work at various sizes (32px to 256px)

### logo.png
- **Size**: 512x512 pixels or larger
- **Format**: PNG with transparency
- **Used by**: Fallback, high-resolution displays

---

## 💡 How the Logo is Used

### 1. Favicon (Browser Tab)
Configured in `index.html`:
```html
<link rel="icon" type="image/svg+xml" href="/logo.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
```

### 2. Header Logo
Used in `Header.tsx`:
```tsx
<img src="/logo.svg" alt="OpAMP Logo" className="h-8 w-8" />
```

### 3. Login Page (Future Enhancement)
Can be added to `LoginPage.tsx`:
```tsx
<img src="/logo.svg" alt="OpAMP Dashboard" className="h-16 w-16 mb-4" />
```

---

## 🎨 Design Recommendations

### Color Scheme
- **Primary Blue**: `#1890ff` (as defined in theme)
- **Accent**: Gray/White for contrast
- **Background**: Transparent for flexibility

### Logo Design
- **Simple**: Works well at 16px (favicon size)
- **Recognizable**: Distinct shape/symbol
- **Scalable**: Vector format (SVG) preferred
- **Contrast**: Works on both light and dark backgrounds

### Icon Concepts
Choose one that represents OpAMP Dashboard:
1. **Network nodes** - Connected dots showing data flow
2. **Monitoring pulse** - Heartbeat/signal wave
3. **Dashboard gauge** - Circular meter/indicator
4. **Data streams** - Flow arrows or pipes
5. **Letter "O"** - Stylized "O" from OpAMP

---

## 🔧 Testing Your Logo

After adding files:

1. **Clear browser cache**: Ctrl+Shift+R or Cmd+Shift+R
2. **Check favicon**: Look at browser tab
3. **Check header**: Visit http://localhost:3000
4. **Check iOS**: Add to home screen on iPhone/iPad
5. **Inspect sources**: Open DevTools → Sources → public folder

---

## 📦 Example: Adding Logo Right Now

```bash
# If you have a logo file ready:
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack/frontend/public/

# Copy your logo (replace with actual path):
cp /path/to/your/logo.svg ./logo.svg
cp /path/to/your/logo.png ./logo.png

# Generate favicons from logo.png:
# Visit https://realfavicongenerator.net/
# Upload logo.png
# Download and extract to this folder

# Rebuild:
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack
docker compose build frontend
docker compose up -d frontend
```

---

## 🔍 Troubleshooting

### Logo not showing?
1. Check file exists: `ls -la frontend/public/`
2. Check browser console for 404 errors
3. Clear browser cache
4. Check file permissions: `chmod 644 frontend/public/logo.svg`

### Favicon not updating?
1. Hard refresh: Ctrl+Shift+R
2. Clear browser cache completely
3. Try incognito/private window
4. Close and reopen browser

### Wrong logo showing?
1. Check Dockerfile copies public folder correctly
2. Verify nginx serves static files
3. Check browser is loading from http://localhost:3000/logo.svg

---

## 📚 Additional Resources

- **Favicon Generator**: https://realfavicongenerator.net/
- **SVG Optimizer**: https://jakearchibald.github.io/svgomg/
- **Logo Maker**: https://logo.com/ or https://www.canva.com/
- **Free Icons**: https://fontawesome.com/ or https://heroicons.com/

---

## ✅ Current Status

- ✅ `public/` folder created
- ✅ `src/assets/` folder created  
- ✅ `index.html` updated with favicon links
- ✅ Header component ready to use logo
- ⏳ **Waiting for**: Your logo files to be added

**Next step**: Add your logo files to `frontend/public/` and rebuild!
