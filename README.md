# Ham Radio Doppler Calculator

```text
$ python .\doppler.py -h
usage: doppler.py [-h] [--position POSITION] satellite channels passes

Calculate recommended memory channels to communicate with an in-orbit satellite.

positional arguments:
  satellite             name of the satellite to track. Searches for the name in the Celestrak database.
  channels              number of recommended memory channels to compute
  passes                number of upcoming passes to average from

options:
  -h, --help            show this help message and exit
  --position POSITION, -p POSITION
                        latitude and longitude of the observer in the format 'LAT,LON'. (Default: Ddtermines location
                        with a request to https://ipinfo.io/loc)

Example: python .\doppler.py ISS 5 2
$ python .\doppler.py ISS 5 5 -p 38.897957,-77.036560
Calculating data for location (38.897957, -77.036560)...
*** Doppler Shift Compensation for ISS (ZARYA) (25544) ***
** Transmitter: Mode V/U FM Voice **
Uplink: 145.800 MHz, Downlink: 437.800 MHz
* Recommended Memory Channels *
Mem     Rx Freq         Tx Freq
M1      437.809 MHz     145.797 MHz
M2      437.805 MHz     145.798 MHz
M3      437.800 MHz     145.800 MHz
M4      437.795 MHz     145.802 MHz
M5      437.791 MHz     145.803 MHz
* Recommended Memory Change Times *
Mem     Shift Time      Rx Freq         Tx Freq
M1      19:24:48        437.810 MHz     145.797 MHz
M2      19:28:43        437.807 MHz     145.798 MHz
M3      19:29:48        437.802 MHz     145.799 MHz
M4      19:30:34        437.798 MHz     145.801 MHz
M5      19:31:39        437.793 MHz     145.802 MHz

** Transmitter: Mode V APRS **
Uplink: 145.825 MHz, Downlink: 145.825 MHz
* Recommended Memory Channels *
Mem     Rx Freq         Tx Freq
M1      145.828 MHz     145.822 MHz
M2      145.827 MHz     145.823 MHz
M3      145.825 MHz     145.825 MHz
M4      145.823 MHz     145.827 MHz
M5      145.822 MHz     145.828 MHz
* Recommended Memory Change Times *
Mem     Shift Time      Rx Freq         Tx Freq
M1      19:24:48        145.828 MHz     145.822 MHz
M2      19:28:43        145.827 MHz     145.823 MHz
M3      19:29:48        145.826 MHz     145.824 MHz
M4      19:30:34        145.824 MHz     145.826 MHz
M5      19:31:39        145.823 MHz     145.827 MHz

[...snip...]

```
