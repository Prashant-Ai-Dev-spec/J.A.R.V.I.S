# Install Playwright Python and browsers
python -m pip install playwright -q
python -m playwright install chromium -q
Write-Output "Playwright installed. To run headless browsing, ensure Chromium is installed."