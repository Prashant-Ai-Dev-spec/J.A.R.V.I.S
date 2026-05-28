# coturn TURN Server Configuration
#
# TURN (Traversal Using Relays around NAT) enables WebRTC connections
# through NAT/firewall by relaying media.

## CURRENT STATUS

# The coturn container is deployed via docker-compose.yml
# Configuration via .env: TURN_EXTERNAL_IP=10.251.190.173

## REQUIRED CONFIGURATION

1. PUBLIC IP ADDRESS (for TURN_EXTERNAL_IP):
   - Set in .env: TURN_EXTERNAL_IP=<your-public-ip>
   - Restart: docker-compose up -d --build coturn

2. PORTS (must be open on firewall):
   - UDP 3478    (STUN / TURN)
   - TCP 3478    (TURN)
   - UDP 5349    (TURN over TLS)
   - TCP 5349    (TURN over TLS)

3. FIREWALL RULES:
   
   AWS Security Group:
   - Inbound: UDP 3478, 5349 from 0.0.0.0/0
   - Inbound: TCP 3478, 5349 from 0.0.0.0/0

   GCP Firewall:
   - Allow ingress tcp:3478,5349 from 0.0.0.0/0
   - Allow ingress udp:3478,5349 from 0.0.0.0/0

   DigitalOcean Firewall:
   - Allow inbound UDP 3478, 5349
   - Allow inbound TCP 3478, 5349

## CURRENT DOCKER-COMPOSE CONFIGURATION

# From docker-compose.yml:

coturn:
  image: instrumentisto/coturn
  ports:
    - "3478:3478/udp"
    - "3478:3478/tcp"
    - "5349:5349/tcp"
    - "5349:5349/udp"
  environment:
    - TURN_PORT=3478
    - TURN_EXTERNAL_IP=<TURN_EXTERNAL_IP>  # Set in .env
  command: [
    "--no-loopback-peers",
    "--no-multicast-peers",
    "--lt-cred-mech",
    "--realm=jarvis",
    "--user=jarvis:turnpassword",
    "--external-ip=<TURN_EXTERNAL_IP>",
    "--listening-port=3478"
  ]
  restart: unless-stopped

## TESTING COTURN CONNECTIVITY

1. Test STUN (discovery):
   curl -v stun:<your-ip>:3478

2. Test with WebRTC client:
   - Visit: https://your-domain/meeting
   - Open browser DevTools → Network → WebRTC Internals
   - Check if "srflx" (server reflexive) candidate appears
   - If no srflx, TURN relay is being used (normal)

3. Using stunclient tool:
   docker run --rm stunclient <your-ip> 3478

4. Using turnutils:
   docker run --rm -it edoburu/turn-server /usr/bin/turnutils_uclient -v -4 -u jarvis -w turnpassword <your-ip>

## ADVANCED CONFIGURATION

For production, consider:

1. Enable TLS (TURNS):
   - Generate certificate: certbot certonly -d your-domain
   - Mount cert into container
   - Add flag: --cert=/path/to/cert.pem --pkey=/path/to/key.pem

2. Use separate TURN instance:
   - Deploy coturn on different server (better performance)
   - Update WebRTC client to use external TURN server

3. Load balancing:
   - Deploy multiple coturn instances
   - Use DNS round-robin or load balancer

4. Monitoring:
   - Enable turnserver stats: --log-file=/var/log/coturn.log
   - Docker logs: docker logs jarvis-coturn-1

## TROUBLESHOOTING

Issue: coturn keeps restarting
Solution: 
  1. Check TURN_EXTERNAL_IP in .env
  2. Verify it's a valid IP (not placeholder)
  3. docker logs jarvis-coturn-1 for errors

Issue: WebRTC works on LAN but not remote
Solution:
  1. Confirm TURN_EXTERNAL_IP is public IP
  2. Check firewall allows UDP 3478, 5349
  3. Verify coturn is running: docker ps | grep coturn

Issue: No relay candidates in browser
Solution:
  1. Might be normal if direct connection works
  2. Test with two clients on different networks
  3. Check WebRTC stats in browser DevTools

## CREDENTIALS

Current default (from docker-compose.yml):
- Realm: jarvis
- Username: jarvis
- Password: turnpassword

For production, change in docker-compose.yml:
  --user=<username>:<password>

Then update WebRTC client or TURN URL if needed.

## DOCKER-COMPOSE OVERRIDE

To use custom coturn configuration, create:
  docker-compose.override.yml

Example:
```yaml
services:
  coturn:
    environment:
      - TURN_EXTERNAL_IP=203.0.113.42
    command: [
      "--no-loopback-peers",
      "--no-multicast-peers",
      "--lt-cred-mech",
      "--realm=jarvis",
      "--user=custom_user:custom_password",
      "--external-ip=203.0.113.42",
      "--listening-port=3478",
      "--log-file=/var/log/coturn.log",
      "--verbose"
    ]
```

Then: docker-compose up -d

## NEXT STEPS

1. ✅ Set TURN_EXTERNAL_IP in .env
2. ✅ Open firewall ports 3478, 5349 (UDP + TCP)
3. ⏳ Restart coturn: docker-compose up -d --build coturn
4. ⏳ Test connectivity from remote client
5. ⏳ Monitor logs: docker logs -f jarvis-coturn-1
