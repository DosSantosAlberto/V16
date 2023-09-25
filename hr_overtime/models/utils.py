# inocencio chipoia

def rule_overtime(time):
    time = str(time).split(':')
    hours = float(time[0])
    minutes = int(time[1])
    seconds = int(time[2])
    if (minutes >= 15) and (minutes <= 44):
        minutes = 30
        _hour = minutes / 60
        hours += _hour
    elif minutes > 44:
        hours += 1

    return hours
