#!/usr/bin/perl
use 5.012;
use warnings;
use File::Copy qw(copy);
use POSIX;

# Run: 'sudo ./update <new_hyperkube>'

my $hyperkubeBin = shift || exit(2);
my $testImage = 'aztest/hyperkube';
my $testTag = strftime("%Y%m%d%H%M%S", localtime(time));
my $targetImage = "$testImage:$testTag";
my $serviceDir = '/etc/systemd/system';
my $manifestsDir = '/etc/kubernetes/manifests';

my $images = `docker images`;
my $baseImage;
if ($images =~/\b(.*hyperkube-.*?)\s+(\S+?)\s/) {
    $baseImage = "$1:$2";
}

my $dockerFile = <<"EOF";
FROM $baseImage
ADD $hyperkubeBin /hyperkube
EOF

# my $hyperkubeBak = 'hyperkube.bak';
# system("docker cp $baseImage/hyperkube $hyperkubeBak") unless ( -e $hyperkubeBak );

open( my $FL, '>', 'Dockerfile' ) or exit(2);
print $FL $dockerFile;
close $FL;

say('Cleaning up containers.');
system('systemctl stop kubelet');
system('docker stop $(docker ps -a -q)');
system('docker rm $(docker ps -a -q) &');

system("docker build -t $targetImage .");

my $updateImage = sub { s/image: ".*"/image: "$targetImage"/ or s/--v=2/--v=10/;};

editWithBackup($manifestsDir, 'kube-apiserver.yaml'             , $updateImage);
editWithBackup($manifestsDir, 'kube-controller-manager.yaml'    , $updateImage);
editWithBackup($manifestsDir, 'kube-scheduler.yaml'             , $updateImage);
editWithBackup($serviceDir, 'kubelet.service' , sub {
    s/.*\/hyperkube-amd64:.*/    $targetImage \\/ unless /ExecStartPre/
    or s/--config=/--pod-manifest-path=/;
});

system('systemctl daemon-reload');

print('New hyperkube version: ');
system("docker run $targetImage /hyperkube --version");
#say('Run \'systemctl start kubelet\' to start');
system('systemctl start kubelet');

my $gcm; 
my $retries = 5;

while( --$retries >= 0){
  $gcm = `docker ps |grep controller-manager_kube`;
  last if ($gcm);
  print "Waiting for controller manager... $retries\n";
  sleep 4;
}

if (!$gcm) {
  print "Not found.\n";
  exit(5);
}

if ($gcm =~ /^(\S*)/) {
#  print "Getting: $1.\n";
  print "docker logs -f $1 2>&1 | grep -a loadb \n"

}


sub editWithBackup {
    my ( $dir, $file, $lineEdit ) = @_;
    my $origFile = $file;
    my $targetFile = $dir.'/'.$file;
    copy( $targetFile, $origFile ) or exit(1) unless ( -e $origFile );
    my @lines = do { local @ARGV = $origFile; readline(); };
    &$lineEdit for @lines;
    open( my $FL, '>', $targetFile ) or exit(2);
    print $FL @lines;
    close $FL;
}


