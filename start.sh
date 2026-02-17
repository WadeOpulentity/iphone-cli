#!/bin/bash
# Start WDA + port forwarding in one command.
# Usage: ./start.sh

UDID="${IPHONE_UDID:?Set IPHONE_UDID env var (run: iphone devices)}"
TEAM_ID="${IPHONE_TEAM_ID:?Set IPHONE_TEAM_ID env var (Apple Developer Team ID)}"
WDA_PROJECT="/tmp/WebDriverAgent/WebDriverAgent.xcodeproj"
PORT=8100

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $WDA_PID $FWD_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# Start WDA
echo "Starting WebDriverAgent..."
xcodebuild -project "$WDA_PROJECT" \
    -scheme WebDriverAgentRunner \
    -destination "id=$UDID" \
    -allowProvisioningUpdates \
    DEVELOPMENT_TEAM="$TEAM_ID" \
    test-without-building \
    > /tmp/iphone-cli-wda.log 2>&1 &
WDA_PID=$!

# Wait for WDA to come up
echo "Waiting for WDA..."
for i in $(seq 1 30); do
    if curl -s http://localhost:$PORT/status | grep -q '"ready"' 2>/dev/null; then
        break
    fi
    # Start port forward once WDA process is running
    if [ "$i" -eq 3 ]; then
        pymobiledevice3 usbmux forward $PORT $PORT > /tmp/iphone-cli-fwd.log 2>&1 &
        FWD_PID=$!
    fi
    sleep 1
done

# Check if it worked
if curl -s http://localhost:$PORT/status | grep -q '"ready"' 2>/dev/null; then
    echo "Ready! WDA is running on localhost:$PORT"
    echo "Use 'iphone' commands in another terminal."
    echo "Press Ctrl+C to stop."
    wait $WDA_PID
else
    echo "Failed to start. Check /tmp/iphone-cli-wda.log"
    kill $WDA_PID $FWD_PID 2>/dev/null
    exit 1
fi
