# Public Assets

This folder contains static assets that are served directly by the web server.

## Required Files

Place your logo and favicon files here with the following names:

### Favicons
- `favicon.ico` - Main favicon (16x16, 32x32, 48x48 multi-size)
- `favicon-16x16.png` - 16x16 PNG favicon
- `favicon-32x32.png` - 32x32 PNG favicon
- `apple-touch-icon.png` - 180x180 PNG for iOS devices

### Logo
- `logo.svg` - SVG logo (used as primary favicon and can be used in the app)
- `logo.png` - PNG logo (512x512 or larger for high resolution displays)

## Generating Favicons

You can use online tools to generate all favicon sizes from a single image:
- https://realfavicongenerator.net/
- https://favicon.io/

## File Structure

```
public/
├── favicon.ico           # Multi-size ICO file
├── favicon-16x16.png    # 16x16 favicon
├── favicon-32x32.png    # 32x32 favicon
├── apple-touch-icon.png # 180x180 for iOS
├── logo.svg             # SVG logo
└── logo.png             # PNG logo
```

## Usage in Code

To use the logo in React components:

```tsx
// Option 1: From public folder (recommended for static assets)
<img src="/logo.svg" alt="OpAMP Dashboard" />

// Option 2: Import from src/assets (if you move files there)
import logo from '@/assets/logo.svg';
<img src={logo} alt="OpAMP Dashboard" />
```

## Notes

- Files in `public/` are served at the root path `/`
- They are NOT processed by Vite/build system
- Perfect for favicons, robots.txt, manifest.json, etc.
- Files in `src/assets/` are processed and optimized by Vite
