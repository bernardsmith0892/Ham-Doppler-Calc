#!/usr/bin/python3.9

import ephem, sys, math, requests, json

C = 299_792_458 # m/s
HOUR = 1 / 24
MINUTE = HOUR / 60
SECOND = MINUTE / 60

"""
Computes the doppler shift of a frequency given a relative velocity.

Args:
    f0 (float): The emitted frequency in `MHz`.
    vel (float): The relative velocity between the two objects in `m/s`.
        (+ means getting closer. - means moving away.)

Returns:
    float: The doppler shift in `Hz`.
"""
def doppler_shift(f0, vel):
    f0 = f0 * 1_000_000

    f = ((C / (C + vel)) * f0)
    shift = f0 - f
    return shift

"""
Determines if the current frequency is closer to the right-hand frequency.

Args:
    f (float): The current, tested frequency.
    f_left (float): The frequency we're moving from.
    f_right (float): The frequency we're moving to.

Returns:
    boolean: True if we're closer to `f_right`.
"""
def should_shift_freqs(f, f_left, f_right):
    left_diff = abs(f_left - f)
    right_diff = abs(f_right - f)

    #print(f"{f}, {f_left} ({left_diff}), {f_right} ({right_diff})")
    return left_diff >= right_diff

"""
Computes the doppler shift for a frequency based on the doppler shift
    for a different frequency.

Args:
    f_orig (float): The original frequency in `MHz`.
    f_shift (float): The doppler shift in `Hz`.
    f_new (float): The new frequency in `MHz`.

Returns:
    float: The new doppler shift in `Hz`.
"""
def doppler_convert(f_orig, f_shift, f_new):
    f_orig = f_orig * 1_000_000
    f_new = f_new * 1_000_000

    f = f_orig + f_shift
    doppler_const = f / f_orig
    f_new_shift = doppler_const * f_new
    new_shift = f_new_shift - f_new
    return new_shift

"""
Computes the current doppler shift between an observer and a satellite.

Args:
    obs (ephem.Observer): The observer. Must have an ephem.Date assigned to it.
    sat (ephem.EarthSatellite): The emitting/receiving satellite.
    rx_freq (float): The receive frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.
    tx_freq (float): The transmit frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.

Returns:
    (float, float):
        - The receive doppler shift in `Hz`.
        - The transmit doppler shift in `Hz`.
"""
def compute_doppler(obs, sat, rx_freq=0.0, tx_freq=0.0):
    sat.compute(obs)
    velocity = sat.range_velocity
    tx_shift = doppler_shift(tx_freq, velocity)
    rx_shift = doppler_shift(rx_freq, -1 * velocity)

    return rx_shift, tx_shift


"""
Generates a recommended list of saved frequency to compensate for doppler
    shift during satellite operations.

Args:
    obs (ephem.Observer): The observer. Must have an ephem.Date assigned to it.
    sat (ephem.EarthSatellite): The emitting/receiving satellite.
    AOS (ephem.Date): The time of 'acquisition of signal' for the observer.
    LOS (ephem.Date): The time of 'loss of signal' for the observer.
    intervals (int): How many memory channels to generate.
    rx_freq (float): The receive frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.
    tx_freq (float): The transmit frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.

Returns:
    list< (float, float) >: A list of suggested transmit and receive
        channel frequencies.
        - The doppler-compensated receive frequency in `MHz`.
        - The doppler-compensated transmit frequency in `MHz`.
"""
def compute_doppler_freqs(obs, sat, AOS, LOS, channels=5, rx_freq=0.0, tx_freq=0.0):
    mems = []

    obs.date = AOS
    start_rx, start_tx = compute_doppler(obs, sat, rx_freq, tx_freq)

    obs.date = LOS
    end_rx, end_tx = compute_doppler(obs, sat, rx_freq, tx_freq)

    rx_interval = (end_rx - start_rx) / (channels-1)
    tx_interval = (end_tx - start_tx) / (channels-1)

    for interval in range(channels):            
        shift_rx = start_rx + (rx_interval * interval)
        shift_tx = start_tx + (tx_interval * interval)
        mems.append( [ rx_freq + shift_rx / 1_000_000 , 
                       tx_freq + shift_tx / 1_000_000 ] )
    
    return mems

"""
Computes the doppler shift for each second of this pass to use in an 
    graphing program.

Args:
    obs (ephem.Observer): The observer. Must have an ephem.Date assigned to it.
    sat (ephem.EarthSatellite): The emitting/receiving satellite.
    AOS (ephem.Date): The time of 'acquisition of signal' for the observer.
    LOS (ephem.Date): The time of 'loss of signal' for the observer.
    rx_freq (float): The receive frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.
    tx_freq (float): The transmit frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.

Returns:
    list<int, float, float>:
        - The current second of this pass.
        - The doppler shift of the receive frequency in `Hz`.
        - The doppler shift of the transmit frequency in `Hz`.
"""
def compute_shift_graph(obs, sat, AOS, LOS, rx_freq=0.0, tx_freq=0.0):
    out_data = []
    pass_length = LOS - AOS
    intervals = int( pass_length // SECOND )

    for i in range(intervals):
        obs.date = AOS + (i * SECOND)
        rx_shift, tx_shift, velocity = compute_doppler(obs, sat, rx_freq, tx_freq)
        out_data.append( (i, rx_shift, tx_shift) )
    
    return out_data

"""
Out of the given memories, determine which memory is closest to the
    given frequency.
"""
def best_channel(freq, mems):
    best = -1
    best_diff = 0
    for i in range( len(mems) ):
        diff = abs(mems[i][0] - freq)
        if diff < best_diff or best == -1:
            best = i
            best_diff = diff
    
    return best

"""
Determine when is the optimal time to shift between the stored
    memory channels for satellite operations.

Args:
    obs (ephem.Observer): The observer. Must have an ephem.Date assigned to it.
    sat (ephem.EarthSatellite): The emitting/receiving satellite.
    AOS (ephem.Date): The time of 'acquisition of signal' for the observer.
    LOS (ephem.Date): The time of 'loss of signal' for the observer.
    mems (list<[float, float]>): 2-D list representing the memory channels.
        - 0: The channel's receive frequency.
        - 1: The channel's transmit frequency.
    rx_freq (float): The receive frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.
    tx_freq (float): The transmit frequency for the observer in `MHz`.
        Defaults to `0.0` to represent `not used`.

Returns:
    list<ephem.Date>: The recommended times to switch to the next memory channel.
"""
def compute_shift_times(obs, sat, AOS, LOS, mems, rx_freq=0.0, tx_freq=0.0):
    switch_times = []
    curr_mem = -1
    pass_length = LOS - AOS
    intervals = int( pass_length // SECOND )

    for i in range(intervals):
        obs.date = AOS + (i * SECOND)
        rx_shift, tx_shift = compute_doppler(obs, sat, rx_freq, tx_freq)
        shifted_rx = rx_freq + (rx_shift / 1_000_000)
        shifted_tx = tx_freq + (tx_shift / 1_000_000)
        best_mem = best_channel(shifted_rx, mems)
        if (curr_mem < len(mems) - 1 and curr_mem != best_mem):
            curr_mem = best_mem
            switch_times.append([curr_mem, obs.date, shifted_rx, shifted_tx])            

    return switch_times

"""
Determine the `next_pass` values for a future pass that has an elevation
    of at least `min_elevation` degrees.

Args:
    obs (ephem.Observer): The observer. Must have an ephem.Date assigned to it.
    sat (ephem.EarthSatellite): The observed satellite.
    min_elevation (float): The minimum elevation for the pass in degrees.
    limit (int): How many upcoming passes to check.

Returns:
    The `next_pass` values for the soonest high-elevation pass. If none
        is found, return None.

"""
def next_high_pass(obs, sat, min_elevation=5.0, limit=25):
    try:
        elevation = 0.0
        while (elevation < min_elevation and limit > 0):
            next_pass = obs.next_pass(sat)
            elevation = (next_pass[3] * 360) / (2 * math.pi)
            obs.date = next_pass[4]
            limit -= 0
        
        return next_pass if limit > 0 else None
    except:
        return None


"""
Downloads current amateur satellite TLEs from Celestrak.

Args:
    None

Returns:
    str: Multi-line string containing the entire TLE file.
"""
CELESTRAK_TLE = "https://celestrak.com/NORAD/elements/amateur.txt"
def download_TLEs():
    try:
        req = requests.get(CELESTRAK_TLE)
        return req.text
    except:
        return "ERROR"

"""
Searches through a TLE for a specific satellite.

Args:
    search_text (str): Text to search for.
    search_field (str): Field to search on. Options are 'name' and 'catalog'.
    TLEs (str): Multi-line string containing multiple TLEs.

Returns:
    str: Name of the satellite. Line 0 of the TLE. None if not found.
    str: Line 1 of the TLE. None if not found.
    str: Line 2 of the TLE. None if not found.
"""
def search_for_TLE(search_text, search_field, TLEs):
    lines = TLEs.splitlines()
    for l in range(0, len(lines), 3):
        name = lines[l]
        line1 = lines[l+1]
        line2 = lines[l+2]

        if (search_field == "name"):
            if search_text in name:
                return name, line1, line2
        elif(search_field == "catalog"):
            if search_text == line2.split(' ')[1]:
                return name, line1, line2

    return None, None, None

"""
Downloads the transmitter information for a satellite from SatNOGS.

Args:
    str or int: NORAD catalog ID number for the satellite.

Returns:
    list<dict>: List of transmitters, each containing:
        - 'description': Description of the transmitter.
        - 'uplink': Uplink frequency in MHz. `0.0` if not found.
        - 'downlink': Downlink frequency in MHz. `0.0` if not found.
"""
def lookup_satellite_transmitters(catalog_id):
    try:
        req = requests.get( f"https://db-dev.satnogs.org/api/transmitters/?format=json&satellite__norad_cat_id={catalog_id}" )
        satnogs_json = json.loads(req.text)
        transmitters = []
        for line in satnogs_json:
            uplink = line['uplink_low']
            if (uplink != None):
                uplink /= 1_000_000
            else:
                uplink = 0.0

            downlink = line['downlink_low']
            if (downlink != None):
                downlink /= 1_000_000
            else:
                downlink = 0.0

            transmitters.append( {'description': line['description'], 'uplink': uplink, 'downlink': downlink} )
        
        return transmitters
    except:
        return []

"""
Request the current latitude and longitudes for this user using 'ipinfo.io'.
    Uses that information to request the elevation from 'nationalmap.gov'.

Args:
    None

Returns:
    (str, str, float): Current Latitude, Longitude, and Elevation (m)
"""
def get_current_location():
    try:
        coord_req = requests.get("https://ipinfo.io/loc")
        lat = coord_req.text.split(',')[0].strip()
        lon = coord_req.text.split(',')[1].strip()

        elev_req = requests.get(f"https://nationalmap.gov/epqs/pqs.php?x={lon}&y={lat}&units=Meters&output=json")
        elev = float(json.loads(elev_req.text)['USGS_Elevation_Point_Query_Service']['Elevation_Query']['Elevation'])

        return lat, lon, elev
    except:
        return None, None, None

"""
Sysargs:
    1: Name of the satellite
    2: Number of channels to compute
    3: Number of upcoming passes to average from
"""
def main():
    # Get observer information
    lat, lon, elev = get_current_location()
    my_loc = ephem.Observer()
    my_loc.lat = lat
    my_loc.lon = lon
    my_loc.elev = elev
    print(f"Calculating data for location ({lat}, {lon}) at {elev} meters")

    # Get satellite information
    TLEs = download_TLEs()
    name, line1, line2 = search_for_TLE(sys.argv[1], "name", TLEs)
    if name == None:
        print(f"CANNOT FIND SATELLITE NAME {sys.argv[1]}!!!")
        exit()

    satellite = ephem.readtle(name, line1, line2)
    transmitters = lookup_satellite_transmitters(satellite.catalog_number)

    # Channels and the number of passes to average from
    channels = int(sys.argv[2])
    total_tests = int(sys.argv[3])

    print(f"*** Doppler Shift Compensation for {satellite.name} ({satellite.catalog_number}) ***")
    for transmitter in transmitters:
        print(f"** Transmitter: {transmitter['description']} **")
        print(f"Uplink: {transmitter['uplink']:.3f} MHz, Downlink: {transmitter['downlink']:.3f} MHz")
        min_elevation = 10.0
        memory_sets = []
        

        # ******************************************************************
        # * Compute the recommended channel frequencies for this satellite *
        # ******************************************************************
        for n in range(total_tests):
            next_pass = next_high_pass(my_loc, satellite, min_elevation)

            if (next_pass != None):                
                memory_sets.append( compute_doppler_freqs(my_loc, satellite, next_pass[0], next_pass[4], channels, transmitter['downlink'], transmitter['uplink']) )
            else:
                print("No good passes found...")
                break

        if (next_pass == None):
            break
        
        average_memory = [ [0.0, 0.0] for i in range(channels) ]
        for mem_set in memory_sets:
            for mem, avg_mem in zip(mem_set, average_memory):
                avg_mem[0] += mem[0]
                avg_mem[1] += mem[1]
        
        print("* Recommended Memory Channels *")
        print("Mem\tRx Freq\t\tTx Freq")
        mem_num = 1
        for mem in average_memory:
            mem[0] /= total_tests
            mem[1] /= total_tests
            print(f"M{mem_num}\t{mem[0]:.3f} MHz\t{mem[1]:.3f} MHz")
            mem_num += 1
    
        # ******************************************************************
        # * Compute the recommended channel change times for the next pass *
        # ******************************************************************
        my_loc = ephem.Observer()
        my_loc.lat = lat
        my_loc.lon = lon
        my_loc.elev = elev

        next_pass = next_high_pass(my_loc, satellite, min_elevation)
        
        shift_times = compute_shift_times(my_loc, satellite, next_pass[0], next_pass[4], average_memory, transmitter['downlink'], transmitter['uplink'])   
        
        print("* Recommended Memory Change Times *")
        print("Mem\tShift Time\tRx Freq\t\tTx Freq")
        for s in shift_times:
            print(f"M{s[0]+1}\t{ephem.localtime(s[1]).strftime('%X')}\t{s[2]:.3f} MHz\t{s[3]:.3f} MHz")
        print()

if __name__ == "__main__":
    main()