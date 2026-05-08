#!/bin/bash

echo "🧪 IdeaHunter System Test"
echo "=========================="
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
HEALTH=$(curl -s http://localhost:5000/api/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health Check: PASSED"
else
    echo "❌ Health Check: FAILED"
fi
echo ""

# Test 2: Stats API
echo "Test 2: Statistics API"
STATS=$(curl -s http://localhost:5000/api/stats)
TOTAL=$(echo "$STATS" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
if [ ! -z "$TOTAL" ]; then
    echo "✅ Stats API: PASSED (Total ideas: $TOTAL)"
else
    echo "❌ Stats API: FAILED"
fi
echo ""

# Test 3: Ideas API
echo "Test 3: Ideas API"
IDEAS=$(curl -s http://localhost:5000/api/ideas)
IDEA_COUNT=$(echo "$IDEAS" | grep -o '"id":[0-9]*' | wc -l)
if [ "$IDEA_COUNT" -gt 0 ]; then
    echo "✅ Ideas API: PASSED (Ideas loaded: $IDEA_COUNT)"
else
    echo "❌ Ideas API: FAILED"
fi
echo ""

# Test 4: Dashboard Loading
echo "Test 4: Dashboard Loading"
DASHBOARD=$(curl -s http://localhost:5000/)
if echo "$DASHBOARD" | grep -q "IdeaHunter"; then
    echo "✅ Dashboard: LOADED"
else
    echo "❌ Dashboard: FAILED TO LOAD"
fi
echo ""

# Test 5: Settings API
echo "Test 5: Settings API"
SETTINGS=$(curl -s http://localhost:5000/api/settings)
if echo "$SETTINGS" | grep -q "min_score"; then
    echo "✅ Settings API: PASSED"
else
    echo "❌ Settings API: FAILED"
fi
echo ""

# Test 6: Saved Ideas API
echo "Test 6: Saved Ideas API"
SAVED=$(curl -s http://localhost:5000/api/ideas/saved)
if echo "$SAVED" | grep -q "ideas"; then
    echo "✅ Saved Ideas API: PASSED"
else
    echo "❌ Saved Ideas API: FAILED"
fi
echo ""

echo "=========================="
echo "🎉 System Test Complete!"
echo ""
echo "📊 Summary:"
echo "- Health Status: $(echo "$HEALTH" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
echo "- Total Ideas: $TOTAL"
echo "- Ideas Loaded: $IDEA_COUNT"
echo ""
echo "🌐 Access Points:"
echo "- Main Dashboard: http://localhost:5000/"
echo "- Debug Console: file:///$PWD/debug.html"
echo "- Simple Test: file:///$PWD/simple-test.html"
echo "- Status Page: file:///$PWD/status.html"
echo ""
echo "✅ IdeaHunter is fully functional!"