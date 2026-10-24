# Barspeed — System Requirements & Specifications

This document details the targets, intentions, and functional specifications fulfilled by the current Barspeed implementation.

---

## 1. System Overview & Core Purpose

Barspeed is a real-time barbell velocity and kinematic tracking system designed for weightlifting and strength training analysis. Using a vertical distance sensor (ToF or optical), it measures barbell elevation, computes movement timing and velocities, detects completed repetitions, and serves a live web-based analytics dashboard.

---

## 2. Set Sampling & Range Analysis

### 2.1 Sampling Session Control
- **Manual Start/Stop**: Sampling is initiated via the web interface by clicking **Clear set / Start sampling** and manually ended by clicking **Stop sampling**.
- **Automated Timeout**: A maximum sampling duration of **5 minutes (300 seconds)** is enforced. If 5 minutes elapse without manual termination, sampling automatically completes and analyzes the collected data.
- **Idle Inactivity**: Sensor readings captured while sampling is inactive (stopped/idle) are ignored and do not pollute set buffers or trigger rep logs.

### 2.2 Range Bounds & Limits
- **Highest & Lowest Distance**: At the conclusion of a set, the system identifies the maximum (`highest_distance_m`) and minimum (`lowest_distance_m`) valid distance readings across the sampling window.
- **10% & 90% Threshold Limits**:
  - Total Range of Motion (ROM) = `highest_distance_m - lowest_distance_m`.
  - **10% Limit**: Computed as $10\%$ of upward travel from bottom position.
  - **90% Limit**: Computed as $90\%$ of upward travel from bottom position.
  - **10-90 Travel Distance**: Distance span between 10% and 90% limits ($0.80 \times \text{ROM}$).

### 2.3 Set Lift Speed
- Computes the duration ($t_{10 \rightarrow 90}$) required to travel between the 10% limit and 90% limit during upward movement.
- **Calculated Lift Speed**: $\text{Lift Speed (m/s)} = \frac{\text{Distance}_{10-90}}{\text{Travel Time}_{10-90}}$.

---

## 3. Repetition Detection & Kinematics

### 3.1 Rep Detector Logic
- **Turnaround Detection**: Analyzes direction reversals (extremas) in distance data using debouncing (`debounce_samples`) and refractory window filtering (`MIN_TURNAROUND_INTERVAL_S`) to eliminate jitter and noise.
- **Direction Convention**: Standardized so that decreasing distance corresponds to upward bar movement (adjustable via `up_is_decreasing`).

### 3.2 Per-Rep Metrics
For each detected repetition within a sampled set, the system measures:
1. **Time up (s)**: Duration between crossing the set's 10% limit and 90% limit during the concentric (upward) phase.
2. **Time down (s)**: Duration between crossing the set's 90% limit and 10% limit during the eccentric (downward) phase.
3. **Avg speed up (m/s)**: Average concentric velocity between 10% and 90% limits ($\frac{\text{Distance}_{10-90}}{\text{Time up}}$).
4. **Max speed up (m/s)**: Peak instantaneous velocity achieved during the 10% to 90% concentric window.

---

## 4. Web Interface & Analytics Dashboard

The Flask web application (`webapp/`) provides an interactive interface polling live session data:

### 4.1 Set Analysis Panel
- **Status Indicator**: Live state badge (*IDLE*, *SAMPLING... (elapsed s)*, *COMPLETED*).
- **Control Button**: Dynamic toggle button (**Clear set / Start sampling** vs **Stop sampling**).
- **Summary Metrics**: Displays Highest Distance, Lowest Distance, 10% Limit, 90% Limit, 10-90 Distance, 10-90 Travel Time, and Calculated Lift Speed.
- **State Reset**: Clicking "Clear set / Start sampling" immediately resets previous summary metrics to `-` and clears the reps table.

### 4.2 Reps Table
- Displays detailed metrics for the **Last 5 Reps** of the current set:
  - Rep `#` (Index)
  - `Time up (s)`
  - `Time down (s)`
  - `Avg speed up (m/s)`
  - `Max speed up (m/s)`

---

## 5. Data Persistence & CSV Logging

- **Permanent CSV Logging**: All completed repetitions across all sets are appended to a timestamped CSV log file (`reps_<timestamp>.csv`).
- **Log Schema**:
  - `set_start_time`: ISO-8601 UTC timestamp of set start.
  - `rep_index_in_set`: 0-indexed rep counter within the set.
  - `logged_at`: ISO-8601 UTC timestamp when rep completed.
  - `time_up_s`: Concentric duration (10%-90%).
  - `time_down_s`: Eccentric duration (90%-10%).
  - `avg_speed_up_mps`: Average concentric speed (m/s).
  - `max_speed_up_mps`: Peak concentric speed (m/s).

---

## 6. Hardware Abstraction & Sensor Decoupling

- **Hardware Layer Contract**: Analysis and Web layers depend exclusively on the `DistanceSensor` interface and `Reading(t: float, distance_m: float, valid: bool)` contract.
- **Sensor Drivers**:
  - `VL53L1X`: Primary Time-of-Flight I2C sensor for Raspberry Pi runtime.
  - `Sharp 2Y0A02`: Legacy IR analog sensor via SPI ADC.
  - `DummySensor`: Stand-in synthetic sine-wave generator for PC development and hardware-free unit testing.
