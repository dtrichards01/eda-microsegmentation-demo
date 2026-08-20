#!/usr/bin/env bash
run_ping() {
  local from=$1 dst=$2 label=$3
  echo "--- $label ($from -> $dst)"
  docker exec "$from" ping -I eth1.90 -c 3 -W 2 "$dst" 2>&1 | tail -3
}

run_ping client8 172.16.90.6 "red->blue ALLOW"
run_ping client8 172.16.90.7 "red->green DENY"
run_ping client6 172.16.90.7 "blue->green ALLOW"
run_ping client6 172.16.90.8 "blue->red ALLOW"
run_ping client7 172.16.90.6 "green->blue ALLOW"
run_ping client7 172.16.90.8 "green->red DENY"
run_ping client6 172.16.90.254 "blue->gateway ALLOW"
run_ping client8 172.16.91.1 "red->static-prefix DENY"
