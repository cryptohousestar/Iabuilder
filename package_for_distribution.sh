#!/bin/bash
# Package IABuilder for distribution

VERSION="1.0.0"
OUTPUT_DIR="dist"
PACKAGE_NAME="iabuilder-installer-$VERSION"

echo "📦 Creating IABuilder distribution package..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Copy all files except development artifacts
rsync -av --exclude='.git' \
         --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='.pytest_cache' \
         --exclude='.vscode' \
         --exclude='.claude' \
         --exclude='dist' \
         --exclude='*.log' \
         --exclude='debug_test.txt' \
         --exclude='test_real.txt' \
         --exclude='tests/' \
         --exclude='benchmark*.py' \
         --exclude='*_analysis.py' \
         --exclude='*.md' \
         --exclude='*.txt' \
         ./ "$OUTPUT_DIR/$PACKAGE_NAME/"

# Create platform-specific executables
cp install.sh "$OUTPUT_DIR/$PACKAGE_NAME/"
cp install.command "$OUTPUT_DIR/$PACKAGE_NAME/"
cp install.ps1 "$OUTPUT_DIR/$PACKAGE_NAME/"

# Copy installer and docs
cp installer.py "$OUTPUT_DIR/$PACKAGE_NAME/"
cp INSTALL_README.md "$OUTPUT_DIR/$PACKAGE_NAME/README.md"

# Make scripts executable
chmod +x "$OUTPUT_DIR/$PACKAGE_NAME/install.sh"
chmod +x "$OUTPUT_DIR/$PACKAGE_NAME/install.command"

# Create compressed archive
echo "🗜️  Creating compressed archive..."
cd "$OUTPUT_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME/"

# Calculate size
SIZE=$(du -sh "${PACKAGE_NAME}.tar.gz" | cut -f1)

echo "✅ Package created successfully!"
echo "📁 Location: $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
echo "📏 Size: $SIZE"
echo ""
echo "🚀 Distribution files:"
echo "   • ${PACKAGE_NAME}.tar.gz (Universal installer)"
echo "   • install.sh (Linux)"
echo "   • install.command (macOS)"
echo "   • install.ps1 (Windows)"
echo ""
echo "📋 Instructions in: README.md"