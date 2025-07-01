# @mrtkrcm/mcp-puppeteer

A Model Context Protocol server that provides browser automation capabilities using Puppeteer. This server enables LLMs to interact with web pages, take screenshots, and execute JavaScript in a real browser environment.

## Installation

```bash
# Using npm
npm install @mrtkrcm/mcp-puppeteer

# Using yarn
yarn add @mrtkrcm/mcp-puppeteer

# Using pnpm
pnpm add @mrtkrcm/mcp-puppeteer
```

## Features

- 🌐 Browser automation with Puppeteer
- 📸 Screenshot capabilities
- 🔍 Accessibility tree generation
- 🎯 Element targeting with frame support
- 🖱️ User interaction simulation (click, hover, type)
- 📝 Form manipulation
- 🚀 JavaScript execution
- 📊 Console log monitoring

## Quick Start

### Basic Usage

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@mrtkrcm/mcp-puppeteer"]
    }
  }
}
```

### With Remote Chrome

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@mrtkrcm/mcp-puppeteer", "start:remote"],
      "env": {
        "PUPPETEER_BROWSER_WS_ENDPOINT": "ws://chrome-server:3000"
      }
    }
  }
}
```

### Docker Usage

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--init", "-e", "DOCKER_CONTAINER=true", "mcp/puppeteer"]
    }
  }
}
```

## Available Tools

### Navigation & Interaction
- **puppeteer_navigate**: Navigate to any URL
- **puppeteer_click**: Click elements using CSS selectors
- **puppeteer_hover**: Hover over elements
- **puppeteer_fill**: Fill form inputs
- **puppeteer_select**: Handle SELECT elements

### Visual & Debugging
- **puppeteer_screenshot**: Capture page/element screenshots
- **puppeteer_evaluate**: Execute JavaScript code
- **browser_snapshot**: Generate accessibility snapshots

### Resource Access
- Console Logs: `console://logs`
- Screenshots: `screenshot://<name>`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| PUPPETEER_BROWSER_WS_ENDPOINT | WebSocket URL for remote Chrome | - |
| PUPPETEER_SLOW_MO | Operation delay (ms) | 0 |
| PUPPETEER_DEFAULT_VIEWPORT_JSON | Viewport config (JSON) | - |
| PUPPETEER_PROTOCOL_TIMEOUT | DevTools timeout (ms) | 30000 |
| FALLBACK_TO_LOCAL_CHROME | Allow local Chrome fallback | true |
| DOCKER_CONTAINER | Docker-specific settings | false |

## Remote Chrome Setup

### Option 1: Browserless
```bash
docker run -p 3000:3000 ghcr.io/browserless/chromium
```

### Option 2: Chrome Debug Mode
```bash
chrome --remote-debugging-port=3000 --remote-debugging-address=0.0.0.0
```

## Development

### Setup
```bash
# Install dependencies
npm install

# Build
npm run build

# Test
npm test

# Run example
npm run test:example
```

### Docker Build
```bash
docker build -t mcp/puppeteer -f Dockerfile .
```

## Testing

The project includes comprehensive tests for:
- Tool functionality
- Navigation features
- Element interaction
- Frame handling
- Error scenarios
- Accessibility features

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details
