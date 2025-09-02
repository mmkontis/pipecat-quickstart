# Pipecat Development Runner API Reference

This document provides curl commands and API examples for testing the Pipecat Development Runner with different transport types.

## Base URL
```
http://localhost:8080
```

## Health Check

### Check server status
```bash
curl -X GET "http://localhost:8080/health"
```

**Response:**
```json
{
  "status": "healthy",
  "transport": "webrtc"
}
```

## Daily Transport

### Start Daily Session (/start endpoint)

This endpoint creates a new Daily room and spawns a bot instance. Requires `DAILY_API_KEY` environment variable.

```bash
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{
    "createDailyRoom": true,
    "dailyRoomProperties": {
      "start_video_off": true,
      "start_audio_off": false,
      "max_participants": 2,
      "enable_recording": "cloud",
      "start_cloud_recording": true
    },
    "body": {
      "custom_data": "test_session",
      "user_id": "user123",
      "session_type": "voice_bot"
    }
  }'
```

**Response:**
```json
{
  "dailyRoom": "https://your-domain.daily.co/room-name",
  "dailyToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Start Daily Session with Existing Room

```bash
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{
    "createDailyRoom": false,
    "body": {
      "custom_data": "existing_room_session",
      "user_id": "user456"
    }
  }'
```

**Note:** Requires `DAILY_SAMPLE_ROOM_URL` environment variable when not creating a room.

### Daily Recording Configuration

The Daily transport supports recording sessions with the `enable_recording` property. This can be configured in several ways:

#### Via Environment Variable
Set the default recording mode for all sessions:
```bash
export DAILY_ENABLE_RECORDING="cloud"
```

#### Via API Request
Override the recording mode per session in the `dailyRoomProperties`:
```bash
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{
    "createDailyRoom": true,
    "dailyRoomProperties": {
      "enable_recording": "cloud"
    }
  }'
```

#### Auto-Start Recording
Enable automatic recording start when the bot joins:
```bash
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{
    "createDailyRoom": true,
    "dailyRoomProperties": {
      "enable_recording": "cloud",
      "start_cloud_recording": true
    }
  }'
```

#### Complete Recording Configuration Example
Full configuration with all recording options:
```bash
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{
    "createDailyRoom": true,
    "dailyRoomProperties": {
      "enable_recording": "cloud",
      "start_cloud_recording": true,
      "max_participants": 10,
      "enable_chat": true
    },
    "body": {
      "user_id": "bot_session_001",
      "session_type": "voice_bot_with_recording"
    }
  }'
```

#### Recording Options
- `"cloud"` - Store recordings in Daily's cloud storage (recommended)
- `"local"` - Store recordings locally on the server  
- `"raw-tracks"` - Record individual audio/video tracks separately
- `null` or omit - Disable recording (default if not configured)

#### Recording Parameters
- `enable_recording` - Sets the recording mode for the room
- `start_cloud_recording` - Boolean to auto-start recording when bot joins (requires `enable_recording` to be set)

#### Auto-Recording on Participant Join
The bot automatically starts recording when the first participant joins the room. This feature:

- Requires `DAILY_API_KEY` environment variable to be set
- Works independently of the `start_cloud_recording` token property
- Triggers recording via Daily REST API when `on_first_participant_joined` event fires
- Uses cloud recording by default
- Logs recording status to the console

To use this feature:
1. Set `DAILY_API_KEY` in your environment variables
2. Ensure `enable_recording` is set to `"cloud"` in the room properties
3. The bot will automatically start recording when the first participant joins

## Telephony Transports

### Twilio Webhook

Handle incoming Twilio calls. Requires public proxy setup.

```bash
curl -X POST "http://your-proxy.ngrok.io/twilio/webhook" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'CallSid=CA123456789&From=%2B1234567890&To=%2B0987654321&CallStatus=ringing'
```

### Telnyx Webhook

Handle incoming Telnyx calls.

```bash
curl -X POST "http://your-proxy.ngrok.io/telnyx/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "call.initiated",
    "payload": {
      "call_control_id": "v3_123456789",
      "call_leg_id": "123456789-abcdef",
      "call_state": "parked",
      "from": "+1234567890",
      "to": "+0987654321"
    }
  }'
```

### Plivo Webhook

Handle incoming Plivo calls.

```bash
curl -X POST "http://your-proxy.ngrok.io/plivo/webhook" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'CallUUID=12345678-1234-1234-1234-123456789012&From=%2B1234567890&To=%2B0987654321&CallStatus=ringing'
```

## WebRTC Transport

### WebRTC Client Access

Access the WebRTC client interface:

```bash
curl -X GET "http://localhost:8080/client"
```

This returns an HTML page with WebRTC client interface.

### WebRTC WebSocket Connection

WebRTC connections are established via WebSocket:

```bash
# WebSocket connection (cannot be tested with curl directly)
ws://localhost:8080/ws
```

## Environment Variables Required

### Daily Transport
```bash
export DAILY_API_KEY="your_daily_api_key"
export DAILY_SAMPLE_ROOM_URL="https://your-domain.daily.co/sample-room"  # Optional
```

### Twilio Transport
```bash
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"
```

### Telnyx Transport
```bash
export TELNYX_API_KEY="your_telnyx_api_key"
```

### Plivo Transport
```bash
export PLIVO_AUTH_ID="your_auth_id"
export PLIVO_AUTH_TOKEN="your_auth_token"
```

## Runner Command Examples

### WebRTC Transport (Default)
```bash
python runner.py
# or explicitly
python runner.py -t webrtc
```

### Daily Transport
```bash
python runner.py -t daily
```

### Daily Direct Connection
```bash
python runner.py -d
```

### Twilio Telephony
```bash
python runner.py -t twilio -x your-proxy.ngrok.io
```

### Telnyx Telephony
```bash
python runner.py -t telnyx -x your-proxy.ngrok.io
```

### Plivo Telephony
```bash
python runner.py -t plivo -x your-proxy.ngrok.io
```

### ESP32 WebRTC Compatibility
```bash
python runner.py -t webrtc --esp32 --host 192.168.1.100
```

### Verbose Logging
```bash
python runner.py -v
```

## Testing Examples

### Complete Daily Session Flow
```bash
# 1. Start the runner
python runner.py -t daily

# 2. In another terminal, create a session
curl -X POST "http://localhost:8080/start" \
  -H "Content-Type: application/json" \
  -d '{"createDailyRoom": true, "body": {"test": true}}'

# 3. Check server health
curl -X GET "http://localhost:8080/health"
```

### WebRTC Client Testing
```bash
# 1. Start the runner
python runner.py -t webrtc

# 2. Open browser to client interface
open http://localhost:8080/client

# 3. Or get the HTML directly
curl -X GET "http://localhost:8080/client"
```

## Error Responses

### Missing Environment Variables
```json
{
  "detail": "DAILY_API_KEY not set"
}
```

### Transport Not Available
```json
{
  "detail": "Daily transport not available"
}
```

## WebSocket Message Formats

### WebRTC Signaling
```json
// Offer from client
{
  "type": "offer",
  "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1..."
}

// Answer from server
{
  "type": "answer",
  "sdp": "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1..."
}
```

### Telephony WebSocket Messages
```json
// Incoming call data
{
  "type": "call_start",
  "call_id": "call_123",
  "from": "+1234567890",
  "to": "+0987654321"
}
```

## Troubleshooting

### Check Available Endpoints
```bash
# Get all routes (requires server running)
curl -X GET "http://localhost:8080/docs"  # FastAPI docs
```

### View Server Logs
```bash
# Run with verbose logging
python runner.py -v
```

### Test WebSocket Connection
```bash
# Use a WebSocket client like wscat
wscat -c ws://localhost:8080/ws
```

## RTVI Compatibility

The Daily `/start` endpoint is RTVI-compatible and can be used with Pipecat client SDKs:

```javascript
// JavaScript client example
const response = await fetch('http://localhost:8080/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    createDailyRoom: true,
    body: { customData: 'test' }
  })
});

const { dailyRoom, dailyToken } = await response.json();
```
