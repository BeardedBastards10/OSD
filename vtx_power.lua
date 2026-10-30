-- vtx_power.lua
-- Direct VTX power / channel control from an RC knob or 6-pos switch, bypassing
-- the stock ArduPilot VTX driver (which cannot send some power levels).
-- Target: ArduPilot 4.4+ on an H7 board (tested design: DAKEFPV H743), analog VTX
-- on SmartAudio or IRC Tramp. Written for the Kimpok AL5810 10W VTX, but the
-- level values are all parameters so it fits other VTXs too.
--
-- Setup (see guide): SCR_ENABLE=1, VTX_ENABLE=0, SERIALn_PROTOCOL=28 on the UART
-- wired to the VTX control pad, SERIALn_OPTIONS=4 (half duplex) for SmartAudio only.
-- Defaults below are for IRC Tramp (power in mW, channel in MHz).
-- Reboot, then tune the VTXA_* parameters.

local PARAM_TABLE_KEY = 101
local PARAM_PREFIX    = 'VTXA_'
local MAV_SEVERITY    = {INFO = 6, WARNING = 4}

local UPDATE_MS   = 100   -- main loop period
local GAP_MS      = 150   -- pause between frames (the VTX needs time to answer)
local NUM_SENDS   = 3     -- times the whole command is repeated (the VTX may miss one)
local STARTUP_MS  = 5000  -- wait for the VTX to boot before the first command

-- name, default
local PARAMS = {
  {'ENABLE',  1},    -- 1 = script active
  {'PROTO',   1},    -- 0 = SmartAudio, 1 = IRC Tramp (default)
  {'BAUD',    0},    -- 0 = protocol default (SA 4800, Tramp 9600)
  {'SER_IDX', 0},    -- which "Scripting" serial port to use (0 = first one)
  {'PWR_CH',  0},    -- RC channel for power (0 = off)
  {'PWR_MODE',0},    -- SmartAudio only: 0 = power INDEX, 1 = power in dBm
  {'BC_CH',   0},    -- RC channel for band/channel presets (0 = off)
  {'DEBUG',   1},    -- 1 = print raw VTX replies to the GCS Messages tab
  -- Six power positions, low -> high on the knob. Value meaning:
  --   -1 = pit mode, otherwise SA index / SA dBm (see PWR_MODE) / Tramp mW
  {'P0', -1}, {'P1', 1000}, {'P2', 2500}, {'P3', 5000}, {'P4', 7500}, {'P5', 10000},
  -- Six channel presets, low -> high on the knob. Value meaning:
  --   0..47 = SmartAudio channel index (band*8+ch; A,B,E,F,R,L), >=100 = MHz
  --   (Tramp always uses MHz). Defaults = Raceband 1..6 in MHz.
  {'C0', 5658}, {'C1', 5695}, {'C2', 5732}, {'C3', 5769}, {'C4', 5806}, {'C5', 5843},
}

assert(param:add_table(PARAM_TABLE_KEY, PARAM_PREFIX, #PARAMS), 'vtx_power: could not add param table')
for i, p in ipairs(PARAMS) do
  assert(param:add_param(PARAM_TABLE_KEY, i, p[1], p[2]), 'vtx_power: could not add ' .. p[1])
end

local function P(name) return param:get(PARAM_PREFIX .. name) end
local function say(sev, msg) gcs:send_text(sev, 'VTXA: ' .. msg) end
local function toint(x) if type(x) == 'number' then return x end return x:toint() end

-- ---------------------------------------------------------------- protocols
-- SmartAudio: AA 55 <cmd<<1|1> <len> <payload> <crc8 poly D5 over everything before it>
local function sa_crc(bytes)
  local crc = 0
  for _, b in ipairs(bytes) do
    crc = crc ~ b
    for _ = 1, 8 do
      if (crc & 0x80) ~= 0 then crc = ((crc << 1) ~ 0xD5) & 0xFF else crc = (crc << 1) & 0xFF end
    end
  end
  return crc
end

local function sa_frame(cmd, payload)
  local f = {0xAA, 0x55, (cmd << 1) | 1, #payload}
  for _, b in ipairs(payload) do f[#f + 1] = b end
  f[#f + 1] = sa_crc(f)
  return f
end

local SA_GET_SETTINGS, SA_SET_POWER, SA_SET_CHANNEL, SA_SET_FREQ, SA_SET_MODE = 1, 2, 3, 4, 5

local function sa_set_power(v)
  if P('PWR_MODE') == 1 then return sa_frame(SA_SET_POWER, {(v & 0x7F) | 0x80}) end  -- dBm
  return sa_frame(SA_SET_POWER, {v & 0xFF})                                           -- index
end
local function sa_set_pit(on)  return sa_frame(SA_SET_MODE, {on and 0x01 or 0x04}) end
local function sa_set_chan(v)
  if v >= 100 then return sa_frame(SA_SET_FREQ, {(v >> 8) & 0x7F, v & 0xFF}) end       -- MHz
  return sa_frame(SA_SET_CHANNEL, {v & 0xFF})
end

-- Tramp: 16 bytes: 0x0F, cmd, value LE (2), zeros, crc = sum(bytes 2..14) at [15]
local function tramp_frame(cmd, value)
  local f = {0x0F, string.byte(cmd), value & 0xFF, (value >> 8) & 0xFF, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
  local sum = 0
  for i = 2, 14 do sum = sum + f[i] end
  f[15] = sum & 0xFF
  return f
end

-- Each builder returns a list of frames to send, in order.
local function build_power(v)
  if P('PROTO') == 1 then
    if v < 0 then return {tramp_frame('I', 0)} end                       -- pit on
    return {tramp_frame('I', 1), tramp_frame('P', v)}                    -- pit off, power mW
  end
  if v < 0 then return {sa_set_pit(true)} end
  return {sa_set_pit(false), sa_set_power(v)}
end

local function build_chan(v)
  if P('PROTO') == 1 then return {tramp_frame('F', v)} end
  return {sa_set_chan(v)}
end

local function build_query()
  if P('PROTO') == 1 then return {tramp_frame('v', 0)} end
  return {sa_frame(SA_GET_SETTINGS, {})}
end

-- ------------------------------------------------------------------ serial
local port = nil
local current_baud = nil

local function open_port()
  local p = serial:find_serial(P('SER_IDX'))
  if p == nil then return false end
  local baud = P('BAUD')
  if baud == 0 then baud = (P('PROTO') == 1) and 9600 or 4800 end
  p:begin(baud)
  p:set_flow_control(0)
  if p.set_stop_bits ~= nil then p:set_stop_bits((P('PROTO') == 1) and 1 or 2) end
  port = p
  current_baud = baud
  say(MAV_SEVERITY.INFO, string.format('serial open, %d baud, %s', baud, P('PROTO') == 1 and 'Tramp' or 'SmartAudio'))
  return true
end

local function send_frames(frames)
  for _, f in ipairs(frames) do
    for _, b in ipairs(f) do port:write(b) end
  end
end

-- collect VTX replies and show them as hex so you can see what the VTX answers
local rx = {}
local function poll_rx()
  local n = toint(port:available())
  if n > 0 then
    while n > 0 do
      local b = port:read()
      if b < 0 then break end
      rx[#rx + 1] = b
      n = toint(port:available())
    end
    return
  end
  if #rx > 0 then
    if P('DEBUG') == 1 then
      local s = {}
      for _, b in ipairs(rx) do s[#s + 1] = string.format('%02X', b) end
      -- SmartAudio settings reply: AA 55 <cmd> <len> chan pwr mode freqH freqL ...
      local txt = table.concat(s, ' ')
      if #rx >= 10 and rx[1] == 0xAA and rx[2] == 0x55 and (rx[3] == 0x01 or rx[3] == 0x09 or rx[3] == 0x11) then
        txt = txt .. string.format('  [chan=%d pwr=%d mode=0x%02X freq=%d]', rx[5], rx[6], rx[7], (rx[8] << 8) | rx[9])
      end
      say(MAV_SEVERITY.INFO, 'rx ' .. txt)
    end
    rx = {}
  end
end

-- ------------------------------------------------------------------- logic
local function switch_pos(ch)
  if ch <= 0 then return nil end
  local pwm = rc:get_pwm(ch)
  if pwm == nil or pwm < 800 then return nil end        -- no RC link
  local pos = math.floor((math.max(1000, math.min(2000, pwm)) - 1000) / (1001 / 6))
  return math.min(5, math.max(0, pos))
end

local pend = {power = nil, chan = nil}   -- {frames=, sends=, last=}
local last_pos = {power = nil, chan = nil}
local stable   = {power = {pos = nil, n = 0}, chan = {pos = nil, n = 0}}
local start_ms = millis()
local was_enabled = false

local function debounce(kind, pos)
  local s = stable[kind]
  if pos == s.pos then s.n = s.n + 1 else s.pos = pos; s.n = 1 end
  return s.n >= 3                    -- 3 identical reads (~300 ms)
end

local function schedule(kind, frames, label)
  pend[kind] = {frames = frames, idx = 1, rounds = 0, last = nil}
  say(MAV_SEVERITY.INFO, label)
end

local function service(kind)
  local p = pend[kind]
  if p == nil then return false end
  local now = millis()
  if p.last ~= nil and toint(now - p.last) < GAP_MS then return false end
  send_frames({p.frames[p.idx]})
  p.last = now
  p.idx = p.idx + 1
  if p.idx > #p.frames then
    p.idx = 1
    p.rounds = p.rounds + 1
    if p.rounds >= NUM_SENDS then pend[kind] = nil end
  end
  return true                         -- at most one frame per tick
end

local function update()
  if P('ENABLE') ~= 1 then was_enabled = false; return update, 1000 end

  if port == nil or current_baud == nil then
    if not open_port() then
      say(MAV_SEVERITY.WARNING, 'no Scripting serial port found (SERIALn_PROTOCOL=28?)')
      return update, 5000
    end
  end

  poll_rx()

  if toint(millis() - start_ms) < STARTUP_MS then return update, UPDATE_MS end

  if not was_enabled then
    was_enabled = true
    last_pos.power, last_pos.chan = nil, nil
    send_frames(build_query())
  end

  local pp = switch_pos(P('PWR_CH'))
  if pp ~= nil and debounce('power', pp) and pp ~= last_pos.power then
    last_pos.power = pp
    local v = P('P' .. pp)
    schedule('power', build_power(v), string.format('power pos %d -> %s', pp + 1, v < 0 and 'PIT' or tostring(v)))
  end

  local cp = switch_pos(P('BC_CH'))
  if cp ~= nil and debounce('chan', cp) and cp ~= last_pos.chan then
    last_pos.chan = cp
    local v = P('C' .. cp)
    schedule('chan', build_chan(v), string.format('channel pos %d -> %d', cp + 1, v))
  end

  if not service('power') then service('chan') end
  return update, UPDATE_MS
end

say(MAV_SEVERITY.INFO, 'vtx_power loaded; set SERIALn_PROTOCOL=28 and VTXA_PWR_CH')
return update, 1000
