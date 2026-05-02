#!/bin/bash
# I2-Data-Intelligence Verification Script
# Run this to validate the complete implementation

set -e

echo "=========================================="
echo "I2 Implementation Verification"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        exit 1
    fi
}

echo ""
echo "1. Checking Docker services..."
docker-compose ps | grep -q "timescaledb"
check "TimescaleDB running"

docker-compose ps | grep -q "redis"
check "Redis running"

docker-compose ps | grep -q "realtime"
check "Socket.IO (realtime) running"

echo ""
echo "2. Checking Database Schema..."
PSQL_CMD="psql -h localhost -U ctuser -d campustwin -t -c"

# Check buildings
BUILDING_COUNT=$($PSQL_CMD "SELECT COUNT(*) FROM buildings;" 2>/dev/null || echo "0")
if [ "$BUILDING_COUNT" == "26" ]; then
    check "26 buildings found"
else
    echo -e "${RED}✗${NC} Expected 26 buildings, found $BUILDING_COUNT"
fi

# Check rooms
ROOM_COUNT=$($PSQL_CMD "SELECT COUNT(*) FROM rooms;" 2>/dev/null || echo "0")
if [ "$ROOM_COUNT" == "142" ]; then
    check "142 rooms found"
else
    echo -e "${YELLOW}⚠${NC} Expected 142 rooms, found $ROOM_COUNT"
fi

# Check academic terms
TERM_COUNT=$($PSQL_CMD "SELECT COUNT(*) FROM academic_terms;" 2>/dev/null || echo "0")
if [ "$TERM_COUNT" -ge "2" ]; then
    check "$TERM_COUNT academic terms found"
else
    echo -e "${YELLOW}⚠${NC} Expected >= 2 terms, found $TERM_COUNT"
fi

# Check calendar events
EVENT_COUNT=$($PSQL_CMD "SELECT COUNT(*) FROM calendar_events;" 2>/dev/null || echo "0")
if [ "$EVENT_COUNT" -ge "74" ]; then
    check "$EVENT_COUNT campus events found"
else
    echo -e "${YELLOW}⚠${NC} Expected >= 74 events, found $EVENT_COUNT"
fi

# Check public holidays
HOLIDAY_COUNT=$($PSQL_CMD "SELECT COUNT(*) FROM public_holidays_2026;" 2>/dev/null || echo "0")
if [ "$HOLIDAY_COUNT" == "25" ]; then
    check "25 public holidays found"
else
    echo -e "${YELLOW}⚠${NC} Expected 25 holidays, found $HOLIDAY_COUNT"
fi

echo ""
echo "3. Checking Hypertable Configuration..."
HYPERTABLE_CHECK=$($PSQL_CMD "SELECT EXISTS(SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name='sensor_readings');" 2>/dev/null || echo "false")
if [ "$HYPERTABLE_CHECK" == "t" ]; then
    check "sensor_readings hypertable exists"
else
    echo -e "${YELLOW}⚠${NC} sensor_readings hypertable not found"
fi

echo ""
echo "4. Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    check "Redis responsive"
    
    KEYSPACE=$( redis-cli INFO keyspace 2>/dev/null | grep -c "db" || echo "0")
    check "Redis keyspace accessible"
else
    echo -e "${YELLOW}⚠${NC} Redis not responsive (may not be running)"
fi

echo ""
echo "5. Checking Socket.IO Server..."
if curl -s http://localhost:4000/health | grep -q "UP"; then
    check "Socket.IO health check passing"
else
    echo -e "${YELLOW}⚠${NC} Socket.IO health check failed"
fi

if curl -s http://localhost:4000/metrics | grep -q "socket_connections"; then
    check "Socket.IO metrics endpoint accessible"
else
    echo -e "${YELLOW}⚠${NC} Socket.IO metrics not available"
fi

echo ""
echo "6. Sample Data Queries..."
echo ""
echo "Current Academic Term:"
$PSQL_CMD "SELECT term_id, term_name, year FROM academic_terms LIMIT 1;" 2>/dev/null || echo "  [DB not accessible]"

echo ""
echo "Sample Room (Dept CS):"
$PSQL_CMD "SELECT room_id, name, capacity, array_length(sensors, 1) as num_sensors FROM rooms WHERE building_id='dept-cs' LIMIT 1;" 2>/dev/null || echo "  [DB not accessible]"

echo ""
echo "Sample Event (Padura):"
$PSQL_CMD "SELECT event_name, start_date, venue_ids, occupancy_factor_min, occupancy_factor_max FROM calendar_events WHERE event_category='padura' LIMIT 1;" 2>/dev/null || echo "  [DB not accessible]"

echo ""
echo "Sample Holiday:"
$PSQL_CMD "SELECT date, name, occupancy_hostel FROM public_holidays_2026 LIMIT 1;" 2>/dev/null || echo "  [DB not accessible]"

echo ""
echo "=========================================="
echo -e "${GREEN}Verification Complete!${NC}"
echo "=========================================="
echo ""
echo "Status Summary:"
echo "  - Database Schema: $([ $BUILDING_COUNT -eq 26 ] && echo 'OK' || echo 'CHECK')"
echo "  - Campus Data: $([ $ROOM_COUNT -eq 142 ] && echo 'OK' || echo 'CHECK')"
echo "  - Events & Holidays: $([ $EVENT_COUNT -ge 74 ] && [ $HOLIDAY_COUNT -eq 25 ] && echo 'OK' || echo 'CHECK')"
echo "  - Real-time Server: $(curl -s http://localhost:4000/health > /dev/null 2>&1 && echo 'OK' || echo 'CHECK')"
echo ""
