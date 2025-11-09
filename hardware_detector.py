#!/usr/bin/env python3
"""
Automated Laptop Hardware Detection for BestBuy Marketplace
Runs on Linux Live USB environment - no OS/storage required on laptop

Detects hardware using Linux system commands and maps to BestBuy fields
"""

import subprocess
import json
import re
import argparse
from typing import Dict, Any, Optional
from datetime import datetime


class HardwareDetector:
    """Detects laptop hardware specifications using Linux commands"""

    def __init__(self):
        self.raw_data = {}
        self.bestbuy_data = {}

    def run_command(self, cmd: str) -> str:
        """Execute shell command and return output"""
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            print(f"Error running {cmd}: {e}")
            return ""

    def run_command_with_sudo(self, cmd: str) -> str:
        """Execute shell command with sudo and return output"""
        try:
            result = subprocess.run(
                f"sudo {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            print(f"Error running sudo {cmd}: {e}")
            return ""

    def detect_system_info(self):
        """Detect basic system information using dmidecode"""
        print("🔍 Detecting system information...")

        # Get system information
        dmidecode_system = self.run_command_with_sudo("dmidecode -t system")
        dmidecode_bios = self.run_command_with_sudo("dmidecode -t bios")
        dmidecode_chassis = self.run_command_with_sudo("dmidecode -t chassis")

        self.raw_data['dmidecode_system'] = dmidecode_system
        self.raw_data['dmidecode_bios'] = dmidecode_bios
        self.raw_data['dmidecode_chassis'] = dmidecode_chassis

        # Extract brand/manufacturer
        brand_match = re.search(r'Manufacturer:\s*(.+)', dmidecode_system)
        if brand_match:
            self.raw_data['brand'] = brand_match.group(1).strip()

        # Extract model/product name
        product_match = re.search(r'Product Name:\s*(.+)', dmidecode_system)
        if product_match:
            self.raw_data['model'] = product_match.group(1).strip()

        # Extract serial number
        serial_match = re.search(r'Serial Number:\s*(.+)', dmidecode_system)
        if serial_match:
            self.raw_data['serial'] = serial_match.group(1).strip()

        # Extract UUID
        uuid_match = re.search(r'UUID:\s*(.+)', dmidecode_system)
        if uuid_match:
            self.raw_data['uuid'] = uuid_match.group(1).strip()

        # Extract SKU
        sku_match = re.search(r'SKU Number:\s*(.+)', dmidecode_system)
        if sku_match:
            self.raw_data['sku'] = sku_match.group(1).strip()

        # Extract Family
        family_match = re.search(r'Family:\s*(.+)', dmidecode_system)
        if family_match:
            self.raw_data['family'] = family_match.group(1).strip()

    def detect_processor(self):
        """Detect processor information"""
        print("🔍 Detecting processor...")

        # Use lscpu
        lscpu_output = self.run_command("lscpu")
        self.raw_data['lscpu'] = lscpu_output

        # Extract processor info
        model_match = re.search(r'Model name:\s*(.+)', lscpu_output)
        if model_match:
            self.raw_data['cpu_model'] = model_match.group(1).strip()

        # Extract cores
        cores_match = re.search(r'Core\(s\) per socket:\s*(\d+)', lscpu_output)
        sockets_match = re.search(r'Socket\(s\):\s*(\d+)', lscpu_output)
        if cores_match and sockets_match:
            cores = int(cores_match.group(1))
            sockets = int(sockets_match.group(1))
            self.raw_data['cpu_cores'] = cores * sockets

        # Extract CPU speed
        mhz_match = re.search(r'CPU MHz:\s*([\d.]+)', lscpu_output)
        if mhz_match:
            self.raw_data['cpu_speed_mhz'] = float(mhz_match.group(1))
            self.raw_data['cpu_speed_ghz'] = round(float(mhz_match.group(1)) / 1000, 2)

        # Extract max MHz
        max_mhz_match = re.search(r'CPU max MHz:\s*([\d.]+)', lscpu_output)
        if max_mhz_match:
            self.raw_data['cpu_max_mhz'] = float(max_mhz_match.group(1))
            self.raw_data['cpu_max_ghz'] = round(float(max_mhz_match.group(1)) / 1000, 2)

        # Get CPU cache info from lscpu (more reliable than dmidecode)
        l3_match = re.search(r'L3 cache:\s*(\d+(?:\.\d+)?)\s*([KMG]iB)', lscpu_output)
        if l3_match:
            size = l3_match.group(1)
            unit = l3_match.group(2)
            # Convert MiB to MB for consistency
            unit_converted = unit.replace('iB', 'B')
            self.raw_data['cpu_l3_cache'] = f"{size} {unit_converted} L3"

        # Also get dmidecode processor info for other details
        dmidecode_cpu = self.run_command_with_sudo("dmidecode -t processor")
        self.raw_data['dmidecode_processor'] = dmidecode_cpu

    def detect_memory(self):
        """Detect RAM information"""
        print("🔍 Detecting memory...")

        # Use dmidecode for detailed memory info
        dmidecode_memory = self.run_command_with_sudo("dmidecode -t memory")
        self.raw_data['dmidecode_memory'] = dmidecode_memory

        # Try to get physical RAM size from dmidecode first
        physical_ram_gb = None
        # Find all Memory Device sections with actual installed RAM (exclude "No Module Installed")
        memory_sections = dmidecode_memory.split('Handle')
        installed_ram_sizes = []
        for section in memory_sections:
            if 'Memory Device' in section and 'No Module Installed' not in section:
                # Extract size from this memory device
                size_match = re.search(r'Size:\s*(\d+)\s*GB', section)
                if size_match:
                    installed_ram_sizes.append(int(size_match.group(1)))

        if installed_ram_sizes:
            physical_ram_gb = sum(installed_ram_sizes)

        # Get total memory from /proc/meminfo as fallback
        meminfo = self.run_command("cat /proc/meminfo")
        mem_match = re.search(r'MemTotal:\s*(\d+)\s*kB', meminfo)
        if mem_match:
            mem_kb = int(mem_match.group(1))
            mem_gb_raw = mem_kb / (1024 * 1024)

            # Use physical RAM if detected via dmidecode
            if physical_ram_gb:
                self.raw_data['ram_size_gb'] = physical_ram_gb
            else:
                # Round to nearest standard RAM size (4, 8, 12, 16, 24, 32, 64, etc.)
                standard_sizes = [2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]
                # Find closest standard size
                closest_size = min(standard_sizes, key=lambda x: abs(x - mem_gb_raw))
                self.raw_data['ram_size_gb'] = closest_size

        # Extract RAM type and speed from dmidecode
        ram_type_match = re.search(r'Type:\s*(DDR\d+)', dmidecode_memory)
        if ram_type_match:
            self.raw_data['ram_type'] = ram_type_match.group(1).strip()

        ram_speed_match = re.search(r'Speed:\s*(\d+)\s*MT/s', dmidecode_memory)
        if ram_speed_match:
            self.raw_data['ram_speed'] = f"{ram_speed_match.group(1)} MHz"

        # Extract max RAM capacity
        max_capacity_match = re.search(r'Maximum Capacity:\s*(\d+)\s*(GB|MB)', dmidecode_memory)
        if max_capacity_match:
            capacity = int(max_capacity_match.group(1))
            unit = max_capacity_match.group(2)
            if unit == 'GB':
                self.raw_data['max_ram_capacity_gb'] = capacity
            else:  # MB
                self.raw_data['max_ram_capacity_gb'] = capacity // 1024

        # Extract number of memory slots
        slots_match = re.search(r'Number Of Devices:\s*(\d+)', dmidecode_memory)
        if slots_match:
            self.raw_data['ram_slots_total'] = int(slots_match.group(1))

        # Count installed vs empty slots and check form factor
        form_factors = re.findall(r'Form Factor:\s*(.+)', dmidecode_memory)
        empty_slots = len(re.findall(r'Size:\s*No Module Installed', dmidecode_memory))

        if form_factors:
            # Get the form factor of installed module(s)
            installed_form_factors = [ff.strip() for ff in form_factors if 'No Module' not in ff]
            if installed_form_factors:
                self.raw_data['ram_form_factor'] = installed_form_factors[0]

                # Determine if RAM is soldered
                soldered_indicators = ['Row Of Chips', 'Chip', 'Proprietary Card', 'Unknown']
                is_soldered = any(indicator in installed_form_factors[0] for indicator in soldered_indicators)
                self.raw_data['ram_soldered'] = is_soldered

        # Calculate available slots
        total_slots = self.raw_data.get('ram_slots_total', 0)
        if total_slots > 0:
            self.raw_data['ram_slots_used'] = total_slots - empty_slots
            self.raw_data['ram_slots_available'] = empty_slots
        else:
            # If no slots detected, RAM is likely soldered
            if self.raw_data.get('ram_soldered') is None:
                self.raw_data['ram_soldered'] = True
                self.raw_data['ram_slots_total'] = 0
                self.raw_data['ram_slots_used'] = 0
                self.raw_data['ram_slots_available'] = 0

    def detect_display(self):
        """Detect display information"""
        print("🔍 Detecting display...")

        # Use xrandr to get screen info (requires X session)
        try:
            xrandr_output = self.run_command("xrandr")
            self.raw_data['xrandr'] = xrandr_output

            # Extract resolution
            res_match = re.search(r'(\d+)x(\d+).*?\*', xrandr_output)
            if res_match:
                width = res_match.group(1)
                height = res_match.group(2)
                self.raw_data['screen_resolution'] = f"{width} x {height}"

            # Extract screen size (in mm, convert to inches)
            size_match = re.search(r'(\d+)mm x (\d+)mm', xrandr_output)
            if size_match:
                width_mm = int(size_match.group(1))
                height_mm = int(size_match.group(2))
                # Only use if dimensions are non-zero
                if width_mm > 0 and height_mm > 0:
                    diagonal_mm = (width_mm**2 + height_mm**2)**0.5
                    diagonal_inches = round(diagonal_mm / 25.4, 1)
                    self.raw_data['screen_size_inches'] = diagonal_inches
        except:
            print("  ⚠️  Could not detect display via xrandr (X server not running)")

        # Try using edid-decode if available
        try:
            # Find EDID files
            edid_files = subprocess.run(
                "find /sys/class/drm -name edid",
                shell=True,
                capture_output=True,
                text=True
            ).stdout.strip().split('\n')

            for edid_file in edid_files:
                if edid_file:
                    edid_output = self.run_command_with_sudo(f"edid-decode {edid_file}")
                    if edid_output:
                        self.raw_data['edid'] = edid_output

                        # Extract screen size from EDID
                        screen_match = re.search(r'Maximum image size:\s*(\d+)\s*cm x\s*(\d+)\s*cm', edid_output)
                        if screen_match:
                            width_cm = int(screen_match.group(1))
                            height_cm = int(screen_match.group(2))
                            diagonal_cm = (width_cm**2 + height_cm**2)**0.5
                            diagonal_inches = round(diagonal_cm / 2.54, 1)
                            self.raw_data['screen_size_inches'] = diagonal_inches
                        break
        except:
            print("  ⚠️  Could not decode EDID data")

        # Detect touchscreen via xinput
        try:
            xinput_output = self.run_command("xinput list")
            self.raw_data['xinput'] = xinput_output

            # Look for touchscreen device (exclude touchpads)
            has_touchscreen = False
            for line in xinput_output.split('\n'):
                line_lower = line.lower()
                if 'touch' in line_lower and 'touchpad' not in line_lower:
                    has_touchscreen = True
                    print("  ✅ Touchscreen detected via xinput")
                    break

            self.raw_data['has_touchscreen'] = has_touchscreen

            if not has_touchscreen:
                print("  ℹ️  No touchscreen detected")
        except:
            print("  ⚠️  Could not detect touchscreen via xinput")
            self.raw_data['has_touchscreen'] = None  # Unknown, will prompt user

    def detect_graphics(self):
        """Detect graphics card information"""
        print("🔍 Detecting graphics...")

        # Use lspci to get GPU info
        lspci_vga = self.run_command("lspci")
        self.raw_data['lspci'] = lspci_vga

        # Filter VGA/3D controller lines
        gpu_lines = [line for line in lspci_vga.split('\n') if 'VGA' in line or '3D controller' in line]

        if gpu_lines:
            self.raw_data['gpus'] = gpu_lines

            # Determine if integrated or dedicated
            has_nvidia = any('nvidia' in line.lower() for line in gpu_lines)
            has_amd_discrete = any('amd' in line.lower() and 'radeon' in line.lower() for line in gpu_lines)
            has_intel = any('intel' in line.lower() for line in gpu_lines)

            if has_nvidia or has_amd_discrete:
                self.raw_data['gpu_type'] = "Dedicated or Discrete GPU"
            elif has_intel:
                self.raw_data['gpu_type'] = "Integrated GPU"

            # Extract GPU models separately for integrated and dedicated
            for gpu_line in gpu_lines:
                gpu_line_lower = gpu_line.lower()

                # Extract text after controller type, removing revision
                gpu_match = re.search(r'(?:VGA compatible controller|3D controller):\s*(.+?)(?:\s*\(rev.*\))?$', gpu_line)
                if not gpu_match:
                    continue

                gpu_text = gpu_match.group(1).strip()

                # Try to extract from brackets first (cleaner name)
                bracket_match = re.search(r'\[(.+?)\]', gpu_text)

                # Detect integrated GPU (Intel or AMD APU with Vega)
                if 'intel' in gpu_line_lower:
                    if bracket_match and bracket_match.group(1).strip():
                        self.raw_data['integrated_gpu_model'] = f"Intel {bracket_match.group(1)}"
                    else:
                        self.raw_data['integrated_gpu_model'] = gpu_text

                # Detect AMD integrated GPU (Vega APU)
                elif 'amd' in gpu_line_lower and 'vega' in gpu_line_lower:
                    if bracket_match and bracket_match.group(1).strip():
                        self.raw_data['integrated_gpu_model'] = f"AMD {bracket_match.group(1)}"
                    else:
                        self.raw_data['integrated_gpu_model'] = gpu_text

                # Detect NVIDIA dedicated GPU
                elif 'nvidia' in gpu_line_lower:
                    if bracket_match and bracket_match.group(1).strip():
                        self.raw_data['dedicated_gpu_model'] = f"NVIDIA {bracket_match.group(1)}"
                    else:
                        self.raw_data['dedicated_gpu_model'] = gpu_text

                # Detect AMD dedicated GPU (discrete Radeon with RX)
                elif 'amd' in gpu_line_lower and 'radeon' in gpu_line_lower and 'rx' in gpu_line_lower:
                    if bracket_match and bracket_match.group(1).strip():
                        self.raw_data['dedicated_gpu_model'] = f"AMD {bracket_match.group(1)}"
                    else:
                        self.raw_data['dedicated_gpu_model'] = gpu_text

    def detect_storage(self):
        """Detect storage information"""
        print("🔍 Detecting storage...")

        # Use lsblk to get storage devices
        lsblk_output = self.run_command("lsblk -d -o NAME,SIZE,TYPE,ROTA")
        self.raw_data['lsblk'] = lsblk_output

        # Get detailed info with smartctl or hdparm
        storage_devices = []

        for line in lsblk_output.split('\n')[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 4 and parts[2] == 'disk':
                device_name = parts[0]
                device_size = parts[1]
                is_rotational = parts[3] == '1'

                # Check if device is removable (USB drive)
                try:
                    removable_check = subprocess.run(
                        f"cat /sys/block/{device_name}/removable",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    is_removable = removable_check.stdout.strip() == '1'
                except:
                    is_removable = False

                # Parse size to check if it's a USB stick (< 32 GB)
                size_match = re.match(r'([\d.]+)([KMGT])', device_size)
                if size_match:
                    value = float(size_match.group(1))
                    unit = size_match.group(2)
                    multipliers = {'K': 0.001, 'M': 0.001, 'G': 1, 'T': 1000}
                    size_gb = value * multipliers.get(unit, 1)

                    # Skip if removable OR too small (likely USB)
                    if is_removable or size_gb < 32:
                        print(f"  ⚠️  Skipping {device_name} ({device_size}) - {'removable device' if is_removable else 'too small, likely USB'}")
                        continue

                storage_devices.append({
                    'device': device_name,
                    'size': device_size,
                    'type': 'HDD' if is_rotational else 'SSD'
                })

        self.raw_data['storage_devices'] = storage_devices

        # Calculate total SSD and HDD capacity
        total_ssd_gb = 0
        total_hdd_gb = 0

        for device in storage_devices:
            size_str = device['size']
            # Parse size (e.g., "256G", "1T", "512.1G")
            size_match = re.match(r'([\d.]+)([KMGT])', size_str)
            if size_match:
                value = float(size_match.group(1))
                unit = size_match.group(2)

                # Convert to GB
                multipliers = {'K': 0.001, 'M': 0.001, 'G': 1, 'T': 1000}
                size_gb = value * multipliers.get(unit, 1)

                if device['type'] == 'SSD':
                    total_ssd_gb += size_gb
                else:
                    total_hdd_gb += size_gb

        # Only report storage if internal drives found
        if total_ssd_gb > 0:
            self.raw_data['ssd_capacity_gb'] = round(total_ssd_gb)
        if total_hdd_gb > 0:
            self.raw_data['hdd_capacity_gb'] = round(total_hdd_gb)

        # Add message if no storage found
        if total_ssd_gb == 0 and total_hdd_gb == 0:
            print("  ℹ️  No internal storage detected (laptop may have no SSD/HDD installed)")

        # Detect eMMC storage (always soldered)
        try:
            emmc_check = subprocess.run(
                "ls /dev/mmcblk* 2>/dev/null | wc -l",
                shell=True,
                capture_output=True,
                text=True,
                timeout=2
            )
            has_emmc = int(emmc_check.stdout.strip()) > 0
            self.raw_data['has_emmc_storage'] = has_emmc

            if has_emmc:
                print("  ✅ eMMC storage detected (soldered)")
        except:
            self.raw_data['has_emmc_storage'] = False

        # Detect storage controller type from lspci
        try:
            lspci_storage = subprocess.run(
                "lspci | grep -i 'storage\\|sata\\|nvme\\|mmc'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=2
            ).stdout

            if lspci_storage:
                self.raw_data['lspci_storage'] = lspci_storage.strip()

                # Determine controller type
                if 'nvme' in lspci_storage.lower() or 'non-volatile memory' in lspci_storage.lower():
                    self.raw_data['storage_controller_type'] = 'NVMe'
                elif 'emmc' in lspci_storage.lower() or 'mmc' in lspci_storage.lower():
                    self.raw_data['storage_controller_type'] = 'eMMC'
                elif 'sata' in lspci_storage.lower():
                    self.raw_data['storage_controller_type'] = 'SATA'
                elif 'ahci' in lspci_storage.lower():
                    self.raw_data['storage_controller_type'] = 'SATA (AHCI)'
                else:
                    self.raw_data['storage_controller_type'] = 'Unknown'
        except:
            pass

        # Determine storage soldered confidence
        if self.raw_data.get('has_emmc_storage'):
            # eMMC is always soldered
            self.raw_data['storage_soldered_confidence'] = 'confirmed_soldered'
        elif self.raw_data.get('storage_controller_type') == 'NVMe':
            # NVMe could be socketed M.2 or soldered BGA
            self.raw_data['storage_soldered_confidence'] = 'unknown - M.2 SSD detected, could be socketed or soldered'
        elif self.raw_data.get('storage_controller_type') in ['SATA', 'SATA (AHCI)']:
            # SATA is usually removable (2.5" drive or M.2 SATA)
            self.raw_data['storage_soldered_confidence'] = 'likely_removable - SATA interface typically uses removable drives'
        elif total_ssd_gb == 0 and total_hdd_gb == 0:
            # No storage detected
            self.raw_data['storage_soldered_confidence'] = 'no_storage_detected'
        else:
            self.raw_data['storage_soldered_confidence'] = 'unknown'

    def detect_battery(self):
        """Detect battery information"""
        print("🔍 Detecting battery...")

        # Use upower to get battery info
        try:
            upower_output = self.run_command("upower -i /org/freedesktop/UPower/devices/battery_BAT0")
            self.raw_data['upower'] = upower_output

            # Extract battery capacity - use voltage for accurate conversion
            voltage_match = re.search(r'voltage:\s*([\d.]+)\s*V', upower_output)
            capacity_match = re.search(r'energy-full:\s*([\d.]+)', upower_output)

            if capacity_match:
                wh = float(capacity_match.group(1))
                # Use actual voltage if available, otherwise assume 11.1V
                voltage = float(voltage_match.group(1)) if voltage_match else 11.1
                # Convert Wh to mAh: mAh = (Wh * 1000) / voltage
                mah = round(wh * 1000 / voltage)
                self.raw_data['battery_capacity_mah'] = mah
        except:
            print("  ⚠️  Could not detect battery via upower")

        # Try ACPI
        try:
            acpi_output = self.run_command("acpi -V")
            self.raw_data['acpi'] = acpi_output
        except:
            pass

        # Try /sys/class/power_supply
        try:
            battery_info = subprocess.run(
                "cat /sys/class/power_supply/BAT*/uevent",
                shell=True,
                capture_output=True,
                text=True
            ).stdout
            self.raw_data['battery_sys'] = battery_info

            # Extract from sysfs
            capacity_match = re.search(r'POWER_SUPPLY_CHARGE_FULL=(\d+)', battery_info)
            if capacity_match:
                uah = int(capacity_match.group(1))
                mah = round(uah / 1000)
                self.raw_data['battery_capacity_mah'] = mah
        except:
            pass

    def detect_network(self):
        """Detect network interfaces (WiFi, Bluetooth, Ethernet)"""
        print("🔍 Detecting network interfaces...")

        # Use lspci for network controllers
        lspci_net = subprocess.run(
            "lspci | grep -i 'network\\|ethernet\\|wireless\\|wi-fi'",
            shell=True,
            capture_output=True,
            text=True
        ).stdout
        self.raw_data['lspci_network'] = lspci_net

        # Detect WiFi - check for wireless, wi-fi, wifi, or network controller
        lspci_lower = lspci_net.lower()
        if ('wireless' in lspci_lower or 'wi-fi' in lspci_lower or
            'wifi' in lspci_lower or 'network controller' in lspci_lower):
            self.raw_data['has_wifi'] = True

            # Try to determine WiFi standard
            iwconfig_output = self.run_command("iwconfig")
            if 'IEEE 802.11' in iwconfig_output:
                self.raw_data['wifi_standard'] = "802.11a/b/g/n/ac"  # Generic, would need more detection
        else:
            self.raw_data['has_wifi'] = False

        # Detect Ethernet
        if 'ethernet' in lspci_net.lower():
            self.raw_data['has_ethernet'] = True

        # Detect Bluetooth
        try:
            hciconfig_output = self.run_command("hciconfig")
            if 'hci0' in hciconfig_output:
                self.raw_data['has_bluetooth'] = True
        except:
            pass

    def detect_usb_ports(self):
        """Detect USB ports"""
        print("🔍 Detecting USB ports...")

        # Use lsusb to detect USB controllers
        lsusb_output = self.run_command("lsusb")
        self.raw_data['lsusb'] = lsusb_output

        # Count USB ports via /sys
        try:
            usb_ports = subprocess.run(
                "find /sys/bus/usb/devices/usb* -name 'product' | wc -l",
                shell=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            self.raw_data['usb_port_count'] = int(usb_ports) if usb_ports else 0
        except:
            pass

    def detect_webcam(self):
        """Detect webcam"""
        print("🔍 Detecting webcam...")

        # Check for video devices
        try:
            video_devices = subprocess.run(
                "ls /dev/video* 2>/dev/null | wc -l",
                shell=True,
                capture_output=True,
                text=True
            ).stdout.strip()

            if video_devices and int(video_devices) > 0:
                self.raw_data['has_webcam'] = True
            else:
                self.raw_data['has_webcam'] = False
        except:
            self.raw_data['has_webcam'] = False

    def detect_all(self):
        """Run all detection methods"""
        print("\n" + "="*60)
        print("🚀 Starting Hardware Detection")
        print("="*60 + "\n")

        self.detect_system_info()
        self.detect_processor()
        self.detect_memory()
        self.detect_display()
        self.detect_graphics()
        self.detect_storage()
        self.detect_battery()
        self.detect_network()
        self.detect_usb_ports()
        self.detect_webcam()

        print("\n" + "="*60)
        print("✅ Hardware Detection Complete")
        print("="*60 + "\n")

    def map_to_bestbuy_fields(self):
        """Map detected hardware to BestBuy field structure"""
        print("📋 Mapping to BestBuy fields...")

        self.bestbuy_data = {
            # Core fields
            "BBYCat": "Computers/Laptops",
            "shop_sku": f"SKU-{self.raw_data.get('sku', 'UNKNOWN')}",

            # Brand and Model
            "_Brand_Name_Category_Root_EN": self.raw_data.get('brand', ''),
            "_Model_Number_Category_Root_EN": self.raw_data.get('model', ''),

            # Processor
            "_ProcessorType_3885_CAT_1002_EN": self.raw_data.get('cpu_model', ''),
            "_ProcessorSpeed_3886_CAT_1002_EN": self.raw_data.get('cpu_max_ghz', self.raw_data.get('cpu_speed_ghz', '')),
            "_ProcessorCores_23322_CAT_1002_EN": self.raw_data.get('cpu_cores', ''),
            "_ProcessorCache_3897_CAT_1002_EN": self.raw_data.get('cpu_l3_cache', ''),

            # Memory
            "_RAMSize_9685909_CAT_1002_EN": self.raw_data.get('ram_size_gb', ''),
            "_RAMType_24674_CAT_1002_EN": f"{self.raw_data.get('ram_size_gb', '')} GB {self.raw_data.get('ram_type', '')} {self.raw_data.get('ram_speed', '')}",

            # Storage
            "_SolidStateDriveCapacity_4085597_CAT_1002_EN": self.raw_data.get('ssd_capacity_gb', ''),
            "_HardDiskDriveCapacity_4085566_CAT_1002_EN": self.raw_data.get('hdd_capacity_gb', ''),

            # Display
            "_ScreenSize_3914_CAT_1002_EN": self.raw_data.get('screen_size_inches', ''),
            "_NativeScreenResolution_15195_CAT_1002_EN": self.raw_data.get('screen_resolution', ''),
            "_ScreenResolution_25959883_CAT_1002_EN": self.raw_data.get('screen_resolution', ''),
            "_TouchscreenDisplay_23335_CAT_1002_EN": "Yes" if self.raw_data.get('has_touchscreen') else "No",

            # Graphics
            "_GraphicsCard_15196_CAT_1002_EN": self.raw_data.get('gpu_model', ''),
            "_GraphicsProcessingUnitType_22765592_CAT_1002_EN": self.raw_data.get('gpu_type', ''),

            # Battery
            "_BatteryCapacity_15253_CAT_1002_EN": self.raw_data.get('battery_capacity_mah', ''),

            # Network
            "_IntegratedWiFi_15245_CAT_1002_EN": "Yes" if self.raw_data.get('has_wifi') else "No",
            "_IntegratedBluetooth_15246_CAT_1002_EN": "Yes" if self.raw_data.get('has_bluetooth') else "No",
            "_EthernetPort_6605_CAT_1002_EN": "Yes" if self.raw_data.get('has_ethernet') else "No",

            # Webcam
            "_Webcam_15213_CAT_1002_EN": "Yes" if self.raw_data.get('has_webcam') else "No",
        }

        # Remove empty fields
        self.bestbuy_data = {k: v for k, v in self.bestbuy_data.items() if v}

        print("✅ Mapping complete\n")

    def prompt_manual_fields(self):
        """Prompt user for fields that require visual inspection"""
        print("\n" + "="*60)
        print("👀 Manual Input Required (Quick Visual Check)")
        print("="*60 + "\n")

        # Screen size - prompt if not auto-detected
        if not self.raw_data.get('screen_size_inches') or self.raw_data.get('screen_size_inches') == 0:
            print("⚠️  Screen size could not be auto-detected")
            print("Common laptop sizes: 11.6, 13.3, 14.0, 15.6, 17.3 inches")
            screen_size_input = input("Screen size in inches (e.g., 14.0): ").strip()
            try:
                self.raw_data['screen_size_inches'] = float(screen_size_input)
            except:
                print("  ⚠️  Invalid input, defaulting to 14.0 inches")
                self.raw_data['screen_size_inches'] = 14.0

        # Keyboard Language
        print("Keyboard Language:")
        print("  1. English")
        print("  2. French")
        print("  3. Bilingual")
        choice = input("Select (1-3): ").strip()
        keyboard_lang = {"1": "English", "2": "French", "3": "Bilingual"}.get(choice, "English")
        self.bestbuy_data["_KeyboardLanguage_24678_CAT_1002_EN"] = keyboard_lang

        # Backlit Keyboard
        backlit = input("\nBacklit Keyboard? (y/n): ").strip().lower()
        self.bestbuy_data["_BacklitKeyboard_24680_CAT_1002_EN"] = "Yes" if backlit == 'y' else "No"

        # Touchscreen - only prompt if auto-detection failed
        if self.raw_data.get('has_touchscreen') is None:
            touchscreen = input("\nTouchscreen Display? (y/n): ").strip().lower()
            self.raw_data['has_touchscreen'] = (touchscreen == 'y')
        else:
            # Show auto-detected value
            auto_detected = "Yes" if self.raw_data.get('has_touchscreen') else "No"
            print(f"\nTouchscreen Display: {auto_detected} (auto-detected)")

        # Convertible/Hybrid
        convertible = input("Convertible/Hybrid (folds into tablet)? (y/n): ").strip().lower()
        self.bestbuy_data["_ConvertibleHybridDisplay_36185_CAT_1002_EN"] = "Yes" if convertible == 'y' else "No"

        # Color
        color = input("\nMain Color (e.g., Black, Silver, Grey): ").strip()
        self.bestbuy_data["_Colour_5105_CAT_1002_EN"] = color

        # Product Condition
        print("\nProduct Condition:")
        print("  1. Brand New")
        print("  2. Open Box")
        print("  3. Refurbished Excellent")
        print("  4. Refurbished Good")
        print("  5. Refurbished Fair")
        condition_choice = input("Select (1-5): ").strip()
        condition_map = {
            "1": "Brand New",
            "2": "Open Box",
            "3": "Refurbished Excellent",
            "4": "Refurbished Good",
            "5": "Refurbished Fair"
        }
        self.bestbuy_data["_ProductCondition_20257570_CAT_1002_EN"] = condition_map.get(condition_choice, "Brand New")

        print("\n✅ Manual input complete\n")

    def save_results(self, output_file: str = "laptop_hardware_data.json"):
        """Save results to JSON file"""
        print(f"💾 Saving results to {output_file}...")

        output = {
            "detection_timestamp": datetime.now().isoformat(),
            "raw_hardware_data": self.raw_data,
            "bestbuy_fields": self.bestbuy_data
        }

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"✅ Results saved to {output_file}\n")

        # Also save just the BestBuy fields for easy upload
        bestbuy_only_file = output_file.replace('.json', '_bestbuy_only.json')
        with open(bestbuy_only_file, 'w') as f:
            json.dump(self.bestbuy_data, f, indent=2)

        print(f"✅ BestBuy fields saved to {bestbuy_only_file}\n")

    def print_summary(self):
        """Print detection summary"""
        print("\n" + "="*60)
        print("📊 DETECTION SUMMARY")
        print("="*60 + "\n")

        print(f"Brand:       {self.raw_data.get('brand', 'N/A')}")
        print(f"Model:       {self.raw_data.get('model', 'N/A')}")
        print(f"Processor:   {self.raw_data.get('cpu_model', 'N/A')}")
        print(f"Cores:       {self.raw_data.get('cpu_cores', 'N/A')}")
        print(f"RAM:         {self.raw_data.get('ram_size_gb', 'N/A')} GB {self.raw_data.get('ram_type', '')}")
        print(f"Storage:     SSD: {self.raw_data.get('ssd_capacity_gb', 'N/A')} GB, HDD: {self.raw_data.get('hdd_capacity_gb', 'N/A')} GB")
        print(f"Screen:      {self.raw_data.get('screen_size_inches', 'N/A')}\" @ {self.raw_data.get('screen_resolution', 'N/A')}")
        print(f"Graphics:    {self.raw_data.get('gpu_model', 'N/A')} ({self.raw_data.get('gpu_type', 'N/A')})")
        print(f"Battery:     {self.raw_data.get('battery_capacity_mah', 'N/A')} mAh")
        print(f"WiFi:        {self.raw_data.get('has_wifi', False)}")
        print(f"Bluetooth:   {self.raw_data.get('has_bluetooth', False)}")
        print(f"Webcam:      {self.raw_data.get('has_webcam', False)}")

        print("\n" + "="*60 + "\n")


def main():
    """Main execution"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Laptop Hardware Detector for BestBuy Marketplace'
    )
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload detection results to Supabase database'
    )
    parser.add_argument(
        '--secrets',
        type=str,
        default='secrets.json',
        help='Path to secrets JSON file (default: secrets.json)'
    )
    args = parser.parse_args()

    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     Laptop Hardware Detector for BestBuy Marketplace      ║
║                                                            ║
║  Boot this script from Linux Live USB                     ║
║  No OS or storage required on laptop                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Check if running as root (required for dmidecode)
    import os
    if os.geteuid() != 0:
        print("⚠️  WARNING: This script needs sudo privileges for full detection")
        print("   Run with: sudo python3 hardware_detector.py\n")

    detector = HardwareDetector()

    # Detect all hardware
    detector.detect_all()

    # Map to BestBuy fields
    detector.map_to_bestbuy_fields()

    # Print summary
    detector.print_summary()

    # Prompt for manual fields
    detector.prompt_manual_fields()

    # Upload to Supabase if --upload flag provided
    if args.upload:
        try:
            from supabase_uploader import load_secrets, create_supabase_client, upload_to_database

            print(f"\n📁 Loading secrets from: {args.secrets}")

            # Load secrets
            secrets = load_secrets(args.secrets)
            print("✓ Secrets loaded successfully")

            # Create authenticated Supabase client
            supabase = create_supabase_client(secrets)
            print("✓ Connected to Supabase")

            # Upload to database
            result = upload_to_database(
                supabase=supabase,
                raw_data=detector.raw_data,
                bestbuy_data=detector.bestbuy_data
            )

            # Print result
            print("\n" + "="*60)
            print("📊 UPLOAD SUMMARY")
            print("="*60)
            print(f"Status:      {result['status']}")
            print(f"Model ID:    {result['model_id']}")

            if result['variant_id']:
                print(f"Variant ID:  {result['variant_id']}")
                print(f"Shop SKU:    {result['shop_sku']}")

            print(f"\nMessage: {result['message']}")
            print("="*60 + "\n")

            if result['status'] == 'created':
                print("✅ Next steps:")
                print("   1. Update inventory count in 'laptops' table")
                print("   2. Create additional variants if needed (different RAM/SSD configs)")
                print("   3. Fill manual fields via web UI (laptop_manual_fields)")
                print("   4. Upload product images (laptop_images)")
                print("   5. Create BestBuy listings when ready (bestbuy_listings)\n")
            elif result['status'] == 'exists':
                print("ℹ️  This exact model configuration already exists in the database.")
                print("   No duplicate was created.\n")

        except ImportError:
            print("\n❌ Error: supabase package not installed")
            print("   Install with: pip install supabase\n")
            # Save to JSON as fallback
            detector.save_results()
        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            print(f"   Create {args.secrets} file with your credentials")
            print(f"   Use secrets.json.example as a template\n")
            # Save to JSON as fallback
            detector.save_results()
        except ValueError as e:
            print(f"\n❌ Error: {e}")
            print(f"   Check your {args.secrets} file has all required fields\n")
            # Save to JSON as fallback
            detector.save_results()
        except Exception as e:
            print(f"\n❌ Error uploading to database: {e}")
            print("   Saving to JSON files as fallback...\n")
            # Save to JSON as fallback
            detector.save_results()
    else:
        # Default mode: save to JSON files
        detector.save_results()
        print("✅ All done! JSON files saved.")
        print("   Run with --upload flag to upload to Supabase database instead.\n")


if __name__ == "__main__":
    main()
