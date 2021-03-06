'''
Module to have Loadosophia.org integration
'''
from Tank.Plugins.ApacheBenchmark import ApacheBenchmarkPlugin
from Tank.Plugins.Monitoring import MonitoringPlugin
from Tank.Plugins.Phantom import PhantomPlugin
from Tank.Plugins.WebOnline import WebOnlinePlugin
from tankcore import AbstractPlugin
import StringIO
import gzip
import itertools
import logging
import mimetools
import mimetypes
import os
import urllib2

class LoadosophiaPlugin(AbstractPlugin):
    '''
    Tank plugin with Loadosophia.org uploading 
    '''

    REDIR_TO = "https://loadosophia.org/service/upload/"
    SECTION = 'loadosophia'
    
    @staticmethod
    def get_key():
        return __file__

    def __init__(self, core):
        '''
        Constructor
        '''
        AbstractPlugin.__init__(self, core)
        self.loadosophia = LoadosophiaClient()
        self.loadosophia.results_url = self.REDIR_TO
        self.project_key = None
    
    def configure(self):
        self.loadosophia.address = self.get_option("address", "https://loadosophia.org/uploader/")
        self.loadosophia.token = self.get_option("token", "")
        self.loadosophia.file_prefix = self.get_option("file_prefix", "")
        
        self.project_key = self.get_option("project", '')
        
    def post_process(self, retcode):
        main_file = None
        # phantom
        try:
            phantom = self.core.get_plugin_of_type(PhantomPlugin)
            if phantom.phantom:
                main_file = phantom.phantom.phout_file
        except KeyError:
            self.log.debug("Phantom not found")
            
        # ab
        try:
            apache_bench = self.core.get_plugin_of_type(ApacheBenchmarkPlugin)
            main_file = apache_bench.out_file
        except KeyError:
            self.log.debug("AB not found")
        
        # monitoring
        mon_file = None
        try:
            mon = self.core.get_plugin_of_type(MonitoringPlugin)
            mon_file = mon.data_file
        except KeyError:
            self.log.debug("Monitoring not found")
            
        self.loadosophia.send_results(self.project_key, main_file, [mon_file])

        try:
            web = self.core.get_plugin_of_type(WebOnlinePlugin)
            if not web.redirect:
                web.redirect = self.REDIR_TO
        except KeyError:
            self.log.debug("Web online not found")

        return retcode
    

class LoadosophiaClient:
    ''' Loadosophia service client class '''
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.token = None
        self.address = None
        self.file_prefix = ''
        self.results_url = None
    
    def send_results(self, project, result_file, monitoring_files):
        ''' Send files to loadosophia '''
        if not self.token:
            self.log.warning("Loadosophia.org uploading disabled, please set loadosophia.token option to enable it, get token at https://loadosophia.org/service/upload/token/")
        else:
            if not self.address:
                self.log.warning("Loadosophia.org uploading disabled, please set loadosophia.address option to enable it")
            else:
                self.log.info("Uploading to Loadosophia.org: %s %s %s", project, result_file, monitoring_files)
                if not project:
                    self.log.info("Uploading to default project, please set loadosophia.project option to change this")
                if not result_file or not os.path.exists(result_file) or not os.path.getsize(result_file):
                    self.log.warning("Empty results file, skip Loadosophia.org uploading: %s", result_file)
                else:
                    self.__send_checked_results(project, result_file, monitoring_files)
    
    
    def __send_checked_results(self, project, result_file, monitoring_files):
        ''' internal wrapper to send request '''
        # Create the form with simple fields
        form = MultiPartForm()
        form.add_field('projectKey', project)
        form.add_field('uploadToken', self.token)
        
        # Add main file
        form.add_file_as_string('jtl_file', self.file_prefix + os.path.basename(result_file) + ".gz", self.__get_gzipped_file(result_file))
    
        index = 0
        for mon_file in monitoring_files:
            if not mon_file or not os.path.exists(mon_file) or not os.path.getsize(mon_file):
                self.log.warning("Skipped mon file: %s", mon_file)
                continue
            form.add_file_as_string('perfmon_' + str(index), self.file_prefix + os.path.basename(mon_file) + ".gz", self.__get_gzipped_file(mon_file))
            index += 1
            
        # Build the request
        request = urllib2.Request(self.address)
        request.add_header('User-Agent', 'Yandex.Tank Loadosophia Uploader Module')
        body = str(form)
        request.add_header('Content-Type', form.get_content_type())
        request.add_header('Content-Length', len(body))
        request.add_data(body)

        response = urllib2.urlopen(request)
        if response.getcode() != 202:
            self.log.debug("Full loadosophia.org response: %s", response.read())
            raise RuntimeError("Loadosophia.org upload failed, response code %s instead of 202, see log for full response text" % response.getcode())
        self.log.info("Loadosophia.org upload succeeded, visit %s to see processing status", self.results_url)
        
                
    def __get_gzipped_file(self, result_file):
        ''' gzip file '''
        out = StringIO.StringIO()
        fhandle = gzip.GzipFile(fileobj=out, mode='w')
        fhandle.write(open(result_file, 'r').read())
        fhandle.close()
        return out.getvalue()
    
    

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form.
    http://blog.doughellmann.com/2009/07/pymotw-urllib2-library-for-opening-urls.html """

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return
    
    def get_content_type(self):
        ''' returns content type '''
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file_as_string(self, fieldname, filename, body, mimetype=None):
        ''' add raw string file '''
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def add_file(self, fieldname, filename, file_handle, mimetype=None):
        """Add a file to be uploaded."""
        body = file_handle.read()
        self.add_file_as_string(fieldname, filename, body, mimetype)
        return
    
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


