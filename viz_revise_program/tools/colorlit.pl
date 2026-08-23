#!/usr/bin/perl
# build.sh 의 "색 리터럴" 검사를 Perl 로 한 것. 파이썬 판과 규칙이 같다.
#
# CSS 변수 정의와 인쇄용 흑백 말고는 hex 가 나오면 안 된다.
# 주석 안의 hex 는 세지 않는다 — 왜 그 값인지 적어 둔 설명까지 위반으로 신고하면
# 검사가 주석을 쫓아낸다.
use strict; use warnings;

my $file = shift or die "usage: colorlit.pl <file>\n";
open my $fh, '<:raw', $file or die "$file: $!\n";
my $src = do { local $/; <$fh> }; close $fh;

$src =~ s{/\*.*?\*/}{}gs;                       # 주석 제거

my @bad;
my $i = 0;
for my $line (split /\n/, $src) {
  $i++;
  while ($line =~ /(#[0-9a-fA-F]{6})\b/g) {
    my $hex = $1;
    my $q = quotemeta $hex;
    next if $line =~ /--[a-z0-9-]+\s*:\s*$q/;   # 토큰 정의 자리
    next if uc($hex) =~ /^(\#000000|\#FFFFFF|\#999999)$/;
    my $t = $line; $t =~ s/^\s+//; $t =~ s/\s+$//;
    push @bad, sprintf("%d: %s", $i, substr($t, 0, 90));
  }
}
print STDERR "$_\n" for @bad[0 .. ($#bad > 9 ? 9 : $#bad)];
exit(@bad ? 1 : 0);
