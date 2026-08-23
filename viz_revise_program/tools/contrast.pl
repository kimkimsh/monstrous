#!/usr/bin/perl
# tools/contrast.py 와 같은 검사를 Perl 로 한 것.
#
# 파이썬이 없는 자리에서도 빌드가 돌아야 한다. 검사가 환경 때문에 건너뛰어지면
# 검사가 아니라 장식이 된다. 규칙·쌍 목록·하한은 .py 와 한 글자도 다르지 않다.
# 둘 중 하나만 고치면 어긋나므로, 고칠 일이 생기면 양쪽을 같이 고친다.
use strict; use warnings;

my @PAIRS = (
  ["--fg","--bg"],["--fg","--panel"],["--fg","--panel-2"],
  ["--fg-dim","--bg"],["--fg-dim","--panel"],["--fg-dim","--panel-2"],
  ["--fg-faint","--bg"],["--fg-faint","--panel"],["--fg-faint","--panel-2"],
  ["--ember","--bg"],["--gold","--bg"],["--lime","--bg"],
  ["--coral","--bg"],["--magenta","--bg"],["--plum","--bg"],
  ["--ember","--panel-2"],["--gold","--panel-2"],["--lime","--panel-2"],
  ["--coral","--panel-2"],["--magenta","--panel-2"],["--plum","--panel-2"],
  ["--ink","--ember"],["--ink","--gold"],["--ink","--lime"],
  ["--ink","--coral"],["--ink","--magenta"],["--ink","--plum"],
  ["--ink","--fg-faint"],
);
my $MIN = 4.5;

sub norm { my $h = shift; return length($h) == 3 ? join("", map { $_ x 2 } split //, $h) : $h; }
sub lin  { my $c = shift() / 255; return $c <= 0.03928 ? $c/12.92 : (($c+0.055)/1.055) ** 2.4; }
sub lum  {
  my $h = norm(shift);
  my ($r,$g,$b) = map { hex substr($h, $_, 2) } (0,2,4);
  return 0.2126*lin($r) + 0.7152*lin($g) + 0.0722*lin($b);
}
sub ratio {
  my ($a,$b) = @_;
  my ($la,$lb) = (lum($a), lum($b));
  my ($hi,$lo) = $la > $lb ? ($la,$lb) : ($lb,$la);
  return ($hi+0.05) / ($lo+0.05);
}

my $file = shift or die "usage: contrast.pl <file>\n";
open my $fh, '<:raw', $file or die "$file: $!\n";
my $src = do { local $/; <$fh> }; close $fh;

my ($bad, $seen) = (0, 0);
while ($src =~ /(:root|html\[[^\]]+\](?:\[[^\]]+\])?)[^{]*\{([^}]*)\}/g) {
  my ($scope, $body) = ($1, $2);
  my %vals;
  while ($body =~ /(--[\w-]+)\s*:\s*#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b/g) { $vals{$1} = $2; }
  next unless exists $vals{"--bg"};      # 색을 정의하지 않는 블록 (레이아웃 규칙 등)
  $seen++;
  my $floor = $scope =~ /contrast/ ? 7.0 : $MIN;
  my %need; $need{$_} = 1 for map { @$_ } @PAIRS;
  my @missing = sort grep { !exists $vals{$_} } keys %need;
  if (@missing) {
    printf "%s: 토큰 누락 [%s] — 이 블록에서 다시 선언할 것\n", $scope, join(", ", @missing);
    $bad += @missing;
  }
  for my $p (@PAIRS) {
    my ($fg, $bgk) = @$p;
    next unless exists $vals{$fg} && exists $vals{$bgk};
    my $r = ratio($vals{$fg}, $vals{$bgk});
    if ($r < $floor) { printf "%s: %s on %s = %.2f (< %s)\n", $scope, $fg, $bgk, $r, $floor; $bad++; }
  }
}
if ($seen == 0) { print "색 블록을 하나도 못 찾았다 — 정규식이나 토큰 블록을 확인할 것\n"; exit 1; }
printf "검사한 블록 %d개, 위반 %d건\n", $seen, $bad;
exit($bad ? 1 : 0);
