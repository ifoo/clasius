__author__ = "Philip Pum"
__copyright__ = "Copyright (C) 2012 Philip Pum"
__credits__ = "Scott Williams"
__license__ = "GPL"
__maintainer__ = "Philip Pum"
__email__ = "philippum@gmail.com"
__version__ = "0.1"
__contact__ = "https://github.com/ifoo/clausius"

import sys, os, argparse, ConfigParser as cp, syslog, atexit, signal, time, popen2, datetime

g_default_config_file = "/etc/clausiusd/clausiusd.conf"

g_default_config = {    "pidfile": "/var/run/clausiusd.pid",
                        "samplerate": 1,
                        "datafile": "/var/cache/clausiusd.data",
                        "storeinterval": 10,
                        "unit": "celsius"}

g_data_sources = (  ("/proc/acpi/thermal_zone/THM0/temperature", lambda x: float(x.lstrip('temperature :').rstrip(' C'))),
                    ("/proc/acpi/thermal_zone/THRM/temperature", lambda x: float(x.lstrip('temperature :').rstrip(' C'))),
                    ("/proc/acpi/thermal_zone/THR1/temperature", lambda x: float(x.lstrip('temperature :').rstrip(' C'))),
                    ("/sys/devices/LNXSYSTM:00/LNXTHERM:00/LNXTHERM:01/thermal_zone/temp", lambda x: float(x.rstrip('000'))),
                    ("/sys/bus/acpi/devices/LNXTHERM:00/thermal_zone/temp", lambda x: float(x.rstrip('000'))))

# daemon code from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
# and http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way/
class Clausiusd(object):
    def __init__(self, configfile):
        self.__configfile = configfile
        self.__pidfile = None
        self.__samplerate = None
        self.__datafile = None
        self.__store_interval = None
        self.__unit = None
        try:
            self.__read_config()
        except:
            syslog.syslog("clausiusd can not read config file\n")
            sys.exit(2)
    
    def __create_default_config(self, filename):
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname, 0755)
        with os.fdopen(os.open(filename, os.O_RDWR | os.O_CREAT, 0644), "w+") as configfile:    
            cfg_parser = cp.ConfigParser()
            cfg_parser.add_section("clausiusd")
            for option in g_default_config:
                cfg_parser.set("clausiusd", option, g_default_config[option])
            cfg_parser.write(configfile)
            configfile.close()
        
    
    def __read_config(self):
        if self.__configfile == None:
            self.__configfile = g_default_config_file
        if not os.path.isfile(self.__configfile):
            self.__create_default_config(self.__configfile)
        
        cfg_parser = cp.ConfigParser()
        cfg_parser.read(self.__configfile)
        self.__pidfile = cfg_parser.get("clausiusd", "pidfile")
        self.__samplerate = cfg_parser.get("clausiusd", "samplerate")
        self.__datafile = cfg_parser.get("clausiusd", "datafile")
        self.__store_interval = cfg_parser.get("clausiusd", "storeinterval")
        self.__unit = cfg_parser.get("clausiusd", "unit")
        
    def __daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:                
                sys.exit(0) # exit parent
        except OSError, err:
            syslog.syslog("clausiusd failed to fork: %d (%s)\n" % (err.errno, err.strerror))
            sys.exit(1)
            
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        try:
            pid = os.fork()
            if pid > 0:                
                sys.exit(0) # exit parent
        except OSError, err:
            syslog.syslog("clausiusd failed to fork: %d (%s)\n" % (err.errno, err.strerror))
            sys.exit(1)
            
        import resource
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY:
            maxfd = popen2.MAXFD
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:
                pass
            
        self.__create_pid_file()
        atexit.register(self.__delete_pid_file)
        
    def __check_pid_file(self):
        try:
            pidfile = open(self.__pidfile, "r")
            pid = int(pidfile.read().strip())
            pidfile.close()
            os.kill(pid, 0)
        except (IOError, OSError):
            return None
        else:
            return pid                
                 
    def __create_pid_file(self):
        os.fdopen(os.open(self.__pidfile, os.O_RDWR | os.O_CREAT, 0644), "w+").write("%d\n" % (os.getpid()))
        
    def __delete_pid_file(self):
        os.remove(self.__pidfile)
    
    def start(self):
        pid = self.__check_pid_file()
        if pid != None:
            syslog.syslog("clausiusd already running with pid %d" % (pid))
            sys.exit(2)
            
        self.__daemonize()
        self.run()
    
    def stop(self):
        pid = self.__check_pid_file()
        if pid != None:
            try:
                while True:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError, err:
                errstr = str(err)
                if errstr.find("No such process") > 0:
                    self.__delete_pid_file()
                else:
                    syslog.syslog("clausiusd can not be stopped: %d (%s)\n" % (err.errno, err.strerror))
                    sys.exit(2)
    
    def restart(self):
        self.stop()
        self.start()
        
    def run(self):
        syslog.syslog("clasiusd running ....")
        data_source = self.__scan_data_sources()
        syslog.syslog("reading")
        if data_source:
            syslog.syslog("data_source: %s" % (data_source[0]))
            while True:
                self.__store_data_point(self.__get_data_point(data_source))
                time.sleep(int(self.__samplerate))
                # TODO: implement store_interval

    def __get_data_point(self, source):
        return source[1](open(source[0], "r").read().strip())

    def __store_data_point(self, data_point):
        os.fdopen(os.open(self.__datafile, os.O_RDWR | os.O_CREAT, 0644), "a+").write("%f %c %s\n" % (data_point, self.__unit[0], datetime.datetime.now()))

    def __scan_data_sources(self):
        for source in g_data_sources:
            if os.path.isfile(source[0]):
                return source
        return None

def main():
    parser = argparse.ArgumentParser(description="A daemon for CPU temperature monitoring.", epilog="%s (%s). Visit %s for more information." % (__copyright__, __email__, __contact__))
    parser.add_argument('action', choices=('start', 'stop', 'restart'))
    parser.add_argument("--cfg-file", nargs=1, help="specify the config file")
    args = parser.parse_args()
    
    Clausiusd(args.cfg_file).__getattribute__(args.action)()    

if __name__ == "__main__":
    main()