# ruff: noqa
#!/usr/bin/env python3
"""Pink Floyd prism: four styles, automatic terminal sizing, no dependencies."""
import argparse
import base64
import math
import shutil
import signal
import sys
import zlib
from pathlib import Path

A, B, C = (319, 68), (218, 241), (415, 241)
ENTRY = (273, 147)
TOP, BOTTOM = (355, 131), (375, 169)
COLORS = [(255, 62, 40), (255, 144, 30), (255, 235, 65),
          (110, 235, 80), (70, 195, 255), (190, 135, 255)]
RAMP = ' .:-=+*#%@'
PHOTO = 'c-nM*1-u;9+4t^_opD{i9yj8_-K~M(6etw;wn%9y6bhwC3#2$j3Y1bp2uVn=gdm}~Td@{Ph?0bakfQf{WajML+xN?FSZ4Rm?#`b7dEC6DQqV<7Hw&s!)XkzM;3&}vyi!nfI8jugs`v;8{}nG*4Mj6cicu`-_&U9UZ`4JxXcUTy0vD)Ov1F9sbp;Rp1XVNPDA5<;hZ~k=nsAhKT`~B>g(56?T`}yEVez2~8(z^ZS2G>e^i<&}I(!t}p=$77`NQFnze_i4O}F5Hk5vp)g-_FLMTHmP5pG*8DO&m#%_?cGqC2X9n}N5(9l{&o*J&jMKMg(vF4Juf4qO3Ez?FvW>XuW|1>C$U;L+8Dqr+j?{2O({F@y_WhxY(im@XU!Twu9yxA03<!xENdJDzEIc$w)Kwg-=Vz>ne+S|WTGzrv4jrEq-H4d8V?=WFOicnUAVdo90QWqga-f=hhi5l>(#GIS6odWC)<{t5uMSkxrG3IS0pi9%5&SaG4?U2rA;#tdj9{UQyP#a0F23jp!CU8D~$(lzjPim(|zz8=5A^yo#{JbDSxfote{HP`@zDSsXOmA@2k81NNNQ4yMO4a<YK6iQl2({Y>O1*T@ei};zkWh;mden<&64}A#ZrDhup58=UKSb;8l_)PeA+@HFh?q0=!I{`G|y?`Af4(EIVaM1N|OK=U`HtYl&4tU)S6A2&xYPgJnW9%4ii77nF1D=ZXMY!JPBdRqNE8S7B4osN1_ykr_LqOrHag|^(6@%%T@rBn*C0qe~B;w`QH6R4QLecR=#XZ1e#h<_@1^TWMLBl_RPxzH|dy5oqg*FwCDqm0%W_qP+rijy0;L-`lG+n$g+DJr1Hoyvhg&&SoY~g3BNCi$o)!>yP>{7T%#o&F5G-#wdgh&r~4lpSAErNdt^8^4_*r6u;qH4j$D8U{O@KI`^s4<RoAQLbx2i{BP_`0NDTtLg^4XGo<h&#|D9FiD$1sF|+n4el+$UBW+WPIU8+mGOp>DTgnIKo;(b3EY&a-k4GV#_HN(-JW`z>2}PFJ`##>x>tXxt=XMtdG!eW4Ohlo-%NH%;U?<84qNk7Ope#?Gimj8lio~<bdP`=LT;3f)2L_Unfc>!8?IJK_O9+@=|y&-h%~1ZJ0iAVB)=iuLaCs1wQG7ifL(<WBHK+q)k6cH(k|m2u;{3z)L+<hkc?ds-_zxSrj3F<>IXxI?{!s8qAz6d@o21y5W@Mbwe}opbs(R-r!%&tXNnck-5;}gNYvDQL<v@#*!_|!wF)(OybU<1Nj5Qwhx;G;P&AJ@fEPaP{uL7DF+66A;zofmLw2d{8Zq=J)4q^BYhG22%jb-?MSxF;PR0|oUvbK6wH2^Gm{WU;sp)>5)d{vQBaDV6yo?%Do92apzvL~q<!Ko7T%<$E1JshV$kuH5PIA*B?Adrv)q!7w=LJ7;1DE&4W>c*D3hfpzHZRsTMh{e{4N8KGF=HSFcw@=`fh_59j^v+Y&hV0%l1(sqm*=EZ@}Iom|A#A3YD-j%2M*e(IR1C*{<(;0UQ7;gUk4q=%>k*A%emcE0$8y%d^cqo6U=9DWG}fGjLO3#IMUo*3+0p7o;p^9f06YwWjpqKDrrvJ99tUX}Ey2lJF;Fwz}yMx3_@=X>|qPgM>IcSXZ=&SAd8|QLE5>!u5a&folUz(e5&sMN7Vopu=jzn!_v1iglaul^dIOBWw@g&mO}qMKE(|QnvsvSXcm#)gg!Rl2qL9;0vVWl`rBemSb8rVC=ZQ=^*iXQS1a^P^~e($Qy|g8A?ehz!ggx;Yh!w)K}M%M=?W||Jr&xUC)wB!i2A=EiFA|0>o(xtmC1yCH-8={fx=yr8#~YkS%CUAOTg4gaXPD;4P}I0>n(+a&0Ar@|~#oF8(epcW*k<oaq_J)(n8Sq^h`!fX!-*KI!dr8>~bbq%-p&1%!gU#V`!ksZz-ce*&_F6Ml<EQX7aDR6ffCyju85wV6*CO-ZeiGpE}CAU16iA$Cw3cRiq7H;mv2Yjq?UwWUJyQX}FDYR(F2n5?7XBcYROT$+$d5${Y1tCF*cTJ)anfz-~*<Zrrv*zD3;syKc-s79bfDI%3zyf;!pvq(y2To*_cK3oCoOe?Vj0k{poMbGn)jEb#N$;fnF*fSatDSr#R2%qZ0mnxbDZ|6rKU!q5#Xt)QpRDxGcFdKC}r#Kl__7w~(+=fP+-^%nToAKpcfry)+_yxiSm~5#zOHu_6%veiI*&xbOI-i3cE(l`47nCcYTmaXPlb~EHlHQA?kr|{CwG=^V;G||<9>+Y>ODPoA2iYC+v=r97{3W6jQn{7fte8TE0*>CL6$q(xODO4v$@6M5axFvnpvdvs0&1)tD5?s$;GL-b@U;}M+EidfCT&7O76rW_?HAw%BnZ@^QX+Crsa_WbvjyP%fE^sg5}5gbKA1QrY1)GAZW7a|62Pv2%|L`NmFm<gXLFbVC7l_N>SOT2BkRL?YR&U)R<lzb8&1e>BDswG86ZY{lWKu!HYZQ>rb;oVFXeTl{EPA=)3S64gw(R+BFpP}G4uR9TU$OCdAl2^vZW8CY{6i<gDs)yh%eh9+4sVq2;Xc!WLp9Zc9pO&@;`((p)_^rY3cxB=!u`B!p7_xJ{dj=E`ZBO5a6#SojFy;;QkGC5g6no(HKy+g(ZK+6(D<u=~P-kQk!Bx8DhzeB{@rt3*HVpAt$>%05^lU!geLxzhsY6)k$4ggj#<ATGIPbQ+{#ib(7Q{Q*y=sQwL^NpL@k1<wtrL47RUZ-$g1`PLqKXOVb<%SIRzGfBslg3JBU28mYB{I86F2=w!?7C9+0aH!1ODD_GT-K^eJCtMSgH&55|fw~)<ivq?^S4`Bs-;Q+EUO)q7G(h$y&WzPnmFzyoiJpD>X7Mu2fZ%*lQn1q2vdr>(xX%&Q${2Qs+BJCF@9QpHeV6_;p{JmgLsj8VRot3A0B(5B?`9sf4-ITX0#7I?!FC`5r&6&_7l!{`JqfBH<SE_ZhUY+8b@_7)@R<URRe}*kVj3T{NxoHUzybW^6niAstZ_jqJrKTsTdH^Of+r0P*a6*W~i%hD_keQ0%V08;|B%25x`#CZ4+EhPRl@!6u$@64RPf-MeKu0aQTw&E$^5K58nd4VFdm~YSQTWH|8F#fyIRz<i4k!l5bb}nrf*o9JN9X;Y(m181HnR;weqcm|S)9?AY*YIem@tb2#zOLkyf($+I|WD)g`!>n<%%rXVo@i_=oERU!AAkVP1OnXOK5ll$TXD9kk2Fw?_Mk0PWf*{s|xH<=EJN_sfsXklFLM}fKes{EmW@1?M99c7SN<Hvv`#@ku-(!!Z!od&yzXu2iplu8$Zx1R|}aj`+q>0Eool2$r&uEyH(LLl`IqGEi(bNHT2v{&fn7Ca(1pXTlig>ConZ~`{-$iks<LVv&iUY-V!M}%oFl=-uh|ech$%(!&jz@05Z3vvK9>(AuCouAG35FqYrd}&XQDVZA+`4Hp0pwkg#dFtX5(8fVQq?wA>Wr8)58R1CYw;;Yi>)FQxQo@y3vd=aH2P7;<&;iNPbF%=C+9g(mXyH1BI_y_h))q^XFKj`<t=z6i(sYJ>3(JHN!%7NMVdsECl+1<eMRbiy;xDeui#u6!yvOlF0tBrchtTC!d$!+GIOp9~5T=o>)4$U+N6mGykK1VL3&6*Y4>)2~oWO+|;5qFXGc8GYK@sYTo}W?MW2of{G_K`wFhgaG21=mac~58IAm!3BV?$;1xShpsKalmxM4#SAVm;XDb$Q#d5bc!Itxhat9Y!k0xA`m991C|(}oe%ciC=gfCxwS0_fPSZvQ1sxcGvm~sk(>Oa}hM;8%68b2LEG}u~QBTINkWwSPK9#><;id%JPptO|TB&48qp<@E311DH4S+`N7x*!3k|Hx${6=`HWT8XQ+~7qph%neBxfy-6K?uUG(6hb7EXyKMYootfH>ERN7esW9uVnO_0%w6y12=CP1{|;%Y?BC(QR8crTzC}pC|0^8xO^o)C44=(N#F=Te<o)_%M(TMg*?wG$_upqyt?0J$kseZ`<bJOb;VZ9QTinLdu6PFC1&fx4Rls$CI_wXdx3THH@57EG>!(46+w5!K%OHvCs@Sr#)4r0NN(V{o&fP!5+E7~bh<H$F{$)+z)|aKo`dlNdqYF$>5<GKLnq&(AuN?}G$^tlHx+xBrLzk;40)mPk=+`=<blN4Yk?GJ8}wbefUN=Ouo)XjZp@3rI7$_o14jK+FM=NZ8-Oj^N1#8eMjqUhxH2;b53Qw9OZk{Lg!5K#KQl@?5>>5bTxTKjlu?&5axQAEx1^>A>+M>4Z)vz$!RUrYu4Yt|*k_K?Tt#QHjsZK3XhGA^Cj)OZ45v`k&bj95O?TM72pk6;tu6JKPfD5EpaHS~km0}yIxj$2msEw^Sd1^9!-4n;QwkTk!!vINZU7);ww0vknfbX8uE?SZC~!?r!{r65*)lDl^j65e6?D#?vd1#N2h#X&8i8_KE)K#s^#kYp$*FP2EKw8EQLOwA50pQuk6SqBwvraH%<+)Bg+*{tem?3;Eg4agIvy+MioqVO62%;8dx*Z_C!J%3K))$t#B&T077N7@n{PAgosWNZ*;IrZF~X0PJ`>>Hs7R<70W^Tes-`d;1KpUKBwIMq(F<y%K%;^UyOiW+#xe5x2@@~iMJP)jW`?psn~;PlzOLJ>VzKpvIObx1(n~4h{xa;F?vN~SEb)aS^>0Y8FOgM>FDsui_XbzbEM@VaJe2(;bwAS1v+-1g#(2FY^FYw(&ce+ly~PKlbygy+hNVV<h?nt2SThcQ2dd&4d$Sdd<A7*xlRa*L4s+6<rv7pEKQFrX;jWFwl?rgVVADR8r-&fB9Sxu$%@nZCu>P2sq!XHkL>2@kb8NDt3{AA0A*=@ETwVr6ohWusJXumYKjm0IQXg1Gnw6Q!9{Vk&zd}X{DU{F(`b(hUgamPrF>t`$N%=G3TOwy5uAyc~hM5ZDj90TQ&nWO${GXb(4D|HVy<0x&R`eDPoMP&g5{yM=Q>VVKejnBEgxx9m8)$8|OrXO?Effly|LA}due@#Y=@%V+#cewsajF7(6$*Vzn#SyvQaI`ZEY%QzE1F(_f@Z;^4xj*P3d4<NTI$x*DfEnSYMZ?!$h>uffNuFiSf@>+NSVsSe3fZaq9z@WGD?`|(qtX8t0Z-EF~p`50KRaTF6h+`(=R|Q{gY{KRZax6iAwo4mLg?q=9kXf%XyUhhZ1t$EonhWpR-iPR86MF$xx2nBH_$S$?Q7+jna`N84G@ehCc)~8DJDeC20;g=Hjb1J@nMEI~+7|ub)o-`6X?`CIaaB$TA$JX=9>>f_K2SJ-V>rcN&%r3ky0o=F)-1q)UrCy9ZlFi#X~;$sU#r=(7n7=d9DF$r47IrXumh6D##PW|?w99$dmAO*0U1&_}5zdcbTy=FA++1GXHH@CEt}Q2v4>B7rLdvUzn&>O8!Lx$H_k52YlW7B|lMMtB2D2Vj4S?&E99;8R2~=NAH<8NfyPi<VBy{j2sh$<zHtH_3jXLP^=<$e-<d<^|13J9LiRa=@e=w>#qO9gaL(cs?OXGFJs^wSYDakQ_S2?}378pTTEYpwyy12YlItYrq~8qOYy3*#t3CE|RAK48V~5RyrqHvtrq*^aVFniAlCfuapcM<$RJhYhQTSsCcUx2e7>;%gk}f9UVG>Z~2aw>CYr*GbM-hA1RkJl40(elCW;(gS?U?rGp}`S4)paUMrJ!kW@J+1eyAZ+4U#Grnt30_@*4&P_kG9zbgwH8PYin63q^xLa{Vx;>IUjanp$H_9_qD$R9K!8Zv&ww)^aP>YqkzxksT;L@UN1FQo!jlMb4JqYEoD#cjQH0@z^gEKswKwyMgi6gpASj#e~X{wOeJg-L0X!e*WfucvA=rFk$VvY2B>Wj<cO%2GaCLn>GJ6x2Brou4`;ou)BjI4l<oB8(X!XLbPG7{IjyJ1p0VGCr8IZSy%){3oQHO!LWbWO@;t$C#>TC`pZeQ2wvmA;14+OqrZKcrzNNH`^S?VK0533_V4#)~6V)ya<lBvL%A|hARUql794M*Z%0_-?VMCiQhihX&V@J53LQ~Y^y`g*!hIt*<OfS#<q3P#}rJBbu{5}0;Q(fy6Ty_hqQ|Mg05kJ8RGzQK)yhx1}VTOi`5bcZrmDzGrd992$PLmxY{8<XUf6&0FH`Y4)SH0m_muXK^G*WGrvSW6-W9**iwdV!#Q2j%OPXFoO1=V4ERQsYLFyRrOq2k$$8_Yhne`H$ouCdC|PC{ZDaCH!3w1r0(lC}LCkwbrYOs>k=#r8+l7gVj=;>3zonN^mbjG<A0W4fFA}YYd78qJ;cMG2NZ1|rJ>ZO+?(5ln*Qk5AUF$T<9cH=dwGSP%<=(rTaQ?6@b|{w6$k8mMR8t25Yy<{|?mWZrh3*-eOMA=J;oNZ85CWjVc7?SCtyqVD9DsIM;G!KwZjDTBPIF&n@CdhYnx*gP7y_`_fFi~V0y<!P``Nq{<V74=vtns3a{08ZP?1jM+X3K?oH<BpK~gQUtMGr6;s4c&^ZprL&y2>cV$KQHPs0AM4JGAf8WzmrM;fYg?CY>gY8suv5C9Qriy_daQps1}3Y3$zE0AhT3+T)cVWZ>x+h*=^%rC3MCI-y`R#?@&is4tBY8$*VaqnYxJ^nX-xdT;U2iDdGsRp;`>3V3Gfgu7z4~6b3DxHhSw0uJV^i+@ldr`9lB4?n-(@H}U7<#ZUmxFR*rTr`M&Byd9GKhJP?9*Vy37y7H;JBgW*es^mUyV3sdK$}d0GD!NLokTo0LvHfH9gDp92-;YFn^<%CZ&`4!zyLYORr=`P3qam|0zpb#YDB7ZzR7}q%6*d8l_i|6CU_mcyFWUAN`Fs78=l65{nj+P8CXdB2LaV3pRQC1%-7y;BRoT<vKvTN1XZVldt)E+t|&*&LL)0H*7E`L&J^CC=NRZwolk;r{gaexAWeGQUR4YL-?@g1<<b^=pwev5b!m0U(*2D#Ij@43WX7xhOcX$uDQUvE!1LB`vRL7*piOvbbu9r2@)7iknv`O%>E5|aPUqLzhx4poq*bx<sb=5%U4=Jd3-rZz(V3h{%m997YH1|^`h7fA{Uis&yRh~&r#49q#9JGgPN7#SU^jE&bbz;iih&d^FcsLz-#$7)&C=HBggzn5y~RM8iqu<=E5eozrY`*lUge?mb2JdCah7-#yy`dAZ-9pdrYfjS)hC<N@?J@F_+JIY>WL*2nUVyI|hlcYPbQqaD$pzu6ykRszb+)+x^g8PdumE)h$XT-*zG(8)3wT5g7&`8wn#ZMI`jtG~j@zp)dh!pk+7-Of$4BWaB2Nzvw=8!M*~xfz6@<Wa0_vLS#yt=mR08+5}R<ydA^L)Tb=Egbt-lqegW)=Z%!Am&nq1Na+Gf_vr9l3@W)MVh)y^7lakS)%AiPjKDtPWOCBjIawW;t(lMV^z%+<MF(asY06?-yOfI`^-UHP`P3bB_yGGdIg;W~0<cY0U;?BP#}QPe#o>*tXiMsKOc#<mG$I=fmehqU4opTl>-t+yzUt2UsI7x$w_9syUTlX|%?go<LC;K@F-YNYTW<Q}Gq&94D6Ca5?Ev&n!%To$0bEUubuAHk*#eaHP*);D1-KIv=^7r(ww2gcgd4yJZA`d<!!>l5ux5Q5;C2XfVBEO>O!S&ir2=wnbZpv=bXuml92tCCF27x-$jTrfZv)E)evUcM0I}%=7-w{l%t7>eUIh61VHm`fA{E^bKqmX=nSR;FBCDKaO;8%FQH?C=La<C}W#y@us>%{Gr`+bPU0@3u6_h!&qtJ`XRY)2KveBqCrMr)jMH3Q>N04BdrwI$K8PHMrmkQf)T(eXtY`*87f13OBgguW4dPe!>rs+irmZbTr@KN)%EDLscwY%Oubl?_y?RMPn28<eSYf8hm8$#4AvuPPkOK+HZU1$wU)GPyzs;QR^qhgvBQ<Mds)Ev8FnFzXN#+CrMk*iw*j=<DWJrf2Z4mYjqsF;~>-|*#l-<ZJzN}Xw@-sVg$%d(WbO+?%keqEoOc8nEb;UQ+m8t~hlG)WILpS=($7vK#d@^6&1?2{=*ubKVumFM|_1y;#q>TG&hri!OQ&+L#2RSRn&$gE&*C*n)#ovF|%WhunWzNlsdLu|~-I4_ZOPILux>MtrbmH=A^SkrlTOyBF&-*pb#%x>#4g0d!J&B7uhjnbTi=bCY3SDHbyt7GVxN&6nZ^+89)wg`)*nyOR{wcQaNj?v-h?Y7qLXzjM%X&arE(GW(%GV8*u!eJS8+iciY-4wBbbX|9yDpIr-!%naPZUMqNV3BQT0h|Nww(x8L>Jb>mCW334S-J%Wh~?2QkFH-K0~2!U=zyoDg=s#ie-boBkibzGhhZFe8NT^AV;ZWHerD#?RA5MomdH~UTl)FxC(f|Kni`P;)K}}KOm!{w9;fL>a2bWk$QVM7t($>By%ko##5xWGUH%}yEZ4>GD6&0)0!`OIkuibQ0cUo=j4k~5xHHbVeRlVxZOT0(-D<lLM1~)meuVK>;W;Mka98*kJO$k&X>^a=a*sWKe$h`4nEczZm7_cTo!iW@zB1S>w(Ckm*BVNxZs<)%v^#p6t#rD2r(<;5qG^jZ$8DHa(=n0oO})dn8i7}}%(7`9z7`&#u7L!nb2G8c&=!$v1&-<4pdq0-1p0z)1CMpcq-DnlFeQ@`<iH%au+|2)E<Ckif06^l=8PSO6WW<YTcohrZUDU60sSfry*LQUffptc-#m{kP|>vXbxWQs(<fT_uB-(aeeg}+YdU>obS|cx=eqI)vkGm>XP`g{i&|k>$b@YZ%}qgNlwit$uyY+S2!Ik?&w*WRI`Cy$&)}g`=RLjaQNQXKJ~nRew0vNF8i-@~jfE13jG&y<%hgJ?QE#+$H3tms7&2!3_WK-o)|J1w<mUgJxc$ll2Q1!y^qZ3hKeBz-&6_pP8yOzi>Fidq$4B-6plC&Fl+=c*HH6+_sU4QqZmFG)(h0abYP)AOe6QUx;i%h2#nNhkvaXhe21jh@F>rOqZiIe0uw%~-9V@U+A8s2+4^Rc7wjB^1jsqlV5zvS`+HH<wd1%tYFBb?da3O@Ak)>T>b50#-h_)O0aU3KuY~!#TF}}>tB@>n$n6o1!WU?+PZy*!%v}Ac&p5zrG%)E0l+a9gJF&A=X;T5ztgv}Z#Q7-;!U__?l!p{K}TcEGsad0JU11nquD=7mv@<ZP$6${7w=Axfme0kC{qSB~T+Jf$(?Zd~89J|8~TOIh5al7w7ewTelZ@uTxN!t$^yH&@i&D(~IYV-^rFna4P_C9vMGp@euqBB058Z7-?yyC33m8Ue<9M!$%;GSjsbbL6u=Y^d+AKJEh<L2daM+Jv>+dEgpxIiCh6q`!1rs{QFG)%L@72Tc=+o0RgyBw{{g*_nJO{3isZKlz5tcGJXJ-gvMjo7J&cG)$no?Z3<Xc75N6u3UJ7LcI8VufSF-oz~&2EOaNR2t}kCS}1wI1b~^)q=>)Py>N0B2t?p7sPG?$O3~({HTJZwR#_gIiDbu*3NT55Ju0;e5QI!amo^STKt@!<|vmlAu}hQEOK|)V2ABT%-po`{sBJti{^SR2ovDFp6~d+?Ruz{_`VxQK#4&dgAK2`cEK?ViCx%g`$>PiZ|*P7`R(s6zv!;Hvmbr)#RuMg^Uh~p|MP<jPrd%0z0bUK(|wN^y7{g{#&6R#e3SNJo7Q>;H#!FP44yD_;~lp<?2IGMx%8zu6W2dwESckc_IG>v4Z(^l-KFO_%YPBAI=;T<=#F)VcC0?AW6_lMkN4_)bGPpK+cj?9v~vE)__%I+k3^f`YeO8hsTCVWsctHDTWeaP!!~<dtIHOhj_3;Pj=*jU?C#j<NxU}Sse4W}uxg=O3%q6=)&sBX+OcDTn2tRcjs$=TK@0ZL(23F9fdzpBel|S9t3iZz5GY!X7Xq>#;Oj?r;JOhQ!c<=t*C{{Q#NHITUF66qD$;`Rb>YQ6^|^?PN+{ExbcQ~48%h^MKAe<uUa4siP1P__N)gl#0n`ki95T2wZQ7&o5(p(=R3MjN>%y-HeLwWT(z654NqpdJ1>Y(pfjVlV=3$5Ja`R1>z3}`KYrb0BoBjK;xA&vo@8^B=>C`!o|NJkv@As=qw?5=&V|Uqa*k(KRjGojvY;?z<G0j0E%N^aF14axOJYoFSQ+7Z0yo>KRwYPWB4__tUtf+qVUbOZF>+=Q1=l6S`PZP^;v6o%#es)o`;@9;hC&ep|seFED^^5&FzTA7zs{KbSp4|QV&K>i%>$qjp#swpjqq>9LEB2&F3^tVxq1230P1Bo}(&_76fz=(FgUe2LV8GGoS)GC19y!g(Y4~Q<F)FsGI#$j1DxOmd{dy86fm4b7Y9*{zqYAKIU{+W?<^{3uM<8JX+w)CwK07|pf@cBQ`<@ekAO;n>R#0^^i_qn(pcti`u{1o<!k7DjP&ivqTCB}~LU)sH<SP;Ko{fCH1Es0!T-QS-31sr1TLL()hm8zCNAesbUr;|_UxrZ>c}eWWuo;0}8JeXPBDXMPaQT1(w!8M)^Iv)8v32WKZrHH$`Ii>XdHnHPX3e?jZ+ATT^po#@`q5|KZuqpfcj2<n|2*%Rv;KD9A?IDS#Q~>`-RYnqo9xy(W{dU_;~RrV)dma>8f}$kXGizYA!8<NdB72e{_2`J&+W133-9y)CSUi~f9UP#{h`+TRqdM<@wyMfH81*0AF-C-Css}qD{gm|Tw^c0)L(RtxA<4h6+de%JG{Q~upw&>7`$?yfh+eN`q^GX-rTw4@g2Hu-Mr(X@zoQCg?qQ#n<UmS-{}-un^5bv(hT*UKy(LYSLAla-hj~T34qU=UA_yPycsxcvDcpXjo50hy6ttpUUuq{SBw2h>{ZLieaqz#s5=OJ_zw&s51Bc#aUcqiSfD~9zKTYcufu&Lh(FVT_35BEIeA5z>w0v<#Y6=i)hdF%6>Q=-Z$2!WmhcxD)6A`n2YZY`r2^f-0*M2%CJbQH*+~p{2PXn}uVoZ~T89j9_nExeA20dU(+eM3x$=|s>zDoO?dSh;!_=Q1zR$3sHMi!Ue&zM!ci+#gx5bsXV?g`n+itz<lqvfhe$0<gJ^QfVPTl{Pmu+|GX%lxpV$8Oa2aeyibED0g!^SiQ4XbnvtTekC?Slpk9x-y$ZFW8J+*77rJoA;Urax1D@CEJJx5R57`Jb%vzWBQKZEss|Z?pG@X7Bpiw<{`Ny%(&0-dZtFe15<A`F-ZfJB?L0nX9h#R{Syk?6>7bzo;)dp=<e1N38hqur>P){c_*oYYrN^_`u<B?>}O}?j3h*UAt&(bnHNHuXcN4%@`5uU7p?<xgFJ{>RC<S=nAwhpzcs~MdrY&H>l<hsJa6hetX$!BT8>iy!J}iRtu}KTMpgW2cCw^9Q2U547dWg9`N%x34@sE7n6~|W<h>SI<rX`;5Nr`lve8oq3T(25cw@J5TK(aEA=kv&}fC-W&EgQD4B~x!;rdTnV#plfp7Spi6Rwl4#g~}hK0Z@4DJpl@4o597oG9+QxC6N_3@WqE_wIeSMIp|hGUN0f6S=%&@C9Hf@^A}LgA;UopJj0)4C>X)7~>QNy;FvLDejz|CEAenSSimnzeyL+lP(p8a}>z#3o%MC$tY6-40y3Yk0M7K(lk;;31PH>~YvWXI=j1$Dep=-D|Tyx^CLrr%Zcc>wBK7&w9?C|FW|1U*?;OgHKk4Uwm8rrniA`_ttthRK8mgtq1CUDOfRIth(R$e1^6BcCq5GV&$#Q%Im|Gf2=M!x4QV$WXZAZ%MTf_`oO_o?A^6`%Ahp|jaxir^xHog@x-o!Z`-ot(v7P>+bG_<VQv=b!#o4jvvyZ)xN3WBb|r34#UD`fhcu$0)o^gt@2=Pb8-8~^Y{qUg^6Q>g30zQ?LDj4_;z}hdmxFROOsXyWmvd0_YA`EE#nezuZB^TiP)uv&oyanvWH`Q1)YC8@dM7AhL&1J2l**-{=UJyF9;$BW$b;cu3}!e;46B5g0`Kkieze;rmt6eIg$w7dS-tq%Z@&2W<9F}7_wOek_v3M+x*{J~LqXRHu2U+<Zmm+YZEeK(v46O0{)EX#R0j-;8f~Cp_+H}qp@r@pAKRn=N5WJ|wNOMuNmIelavVQ)qOud$zyvNg2iDpKclL}JGJd<Q4?g*Tv#$KxKUY8ePVd7@et3M{`bXEi_t4VmGvE8wT`%r>_Y0$^Jr~b-&UpA`@%#tQ`%8nR>*`<j*1ton+k1QKy<aEatPIz`=dXLoU-hKD;t^xT9Ao9Z`l`E(&u<gUZ}gX6Ray4C@@Hq(7N6X`<hWs<9X@3FkB6_>Z{*s&Hd?yp$j^Q>@~u4vF8opV-P^YPX+rtb;o*K=?p8HxT*VwzHrvW}qwF@zUROCDT&)giB!g;UPwaFehj&1Tchvm$M%bv98<nJ^R%@$PgK~{)24(LuY$HQ~r&b|}Cabgr_M+ip2fa@kmE^r#hns7GVwSj@nW|Ao3yf%kYHwOPR);7B+bwi=`Md2h>B0+sv2fx2U#?x*`~82HFa2choO{kV?dZ)n9##%i5WA*YutgyW-FmeWf&LE)BkI<0liE4g{Pm#U{JA!CtY2?;%QfIoo|njY90h0DtfOQ+oiboyqk19Oof>Rb(?v7X1zDD~^$Z@q#g1DYa>~!onswh_7R~tUl4<uYp85FNhu-adbb0SXYybP`m!HmG{qXenFZ#!8``+=~s5_tb?|nwhdBJ)7P4U`?_NSk>t=Z5?q+RL7$6D{#m9JM;*8L}1_j0uQ346^W&Z?Qt+8OTZd!5y@!sRo(Rd<wET~l3sVcYUwv@JQRXW1bGmmN54@qQy#A252&fn&Znc-->+M!vt-;1?zjnz3Ws)Q!W_hr5ULxZAdSBkSIP$m|NuW@uJ?qY)VGi9M*J+S4reB%(Vud#Zj{HArgBQWo@)1)-%Zdpvb(D7r4gaKbI7DLSc_BkL=|d2t4Zx+pzOP=$_#dFHx6lNRePHD;QYtxeiw)M;lN_t3-leE#{zy}cV&ulnrK`E$=X_tYJ>pVZNeO|77p!0^!`&#lHWD2=WIilIYlR|p27=Y_>Wal0u8U2@M8gSMJn?HTS>+Dtz(y#O|$z$m?=r8P%ccNf+!XhTvg#>JK_U`V5`Zo#Ih)EXUwhL6~3zx|Fo|EL4c{oT?3xZ~Ux@4M{%SywHZ{g-9a?^-@{-rBiuefRLP-UaJ>pIE>2u~qXQ{PfQ=-u}tmuWUT+#qz9|jJYqVkH7A{@P736XThS?)wN%@{eVE%dwZ(@`VU`Mzgtt?usHbQZTrg?{4XE(*F0jao@1`L&ssCxSu@T4;!c0<E#>7`CM$n8V977KmmWP}#bHC1?Ay6w-|jX04p_G@Xl{cS@7eR-ZXM6>(wMn*<=RQfStF94bO$@u?Xj^jwCQ!!{jw_>q1{%oI~$(Nk5#z_gdM`vAEpI2C9I}q4%$$hpssU$N0x)3Q9lG-r)UW$B(Ni~R8kmIA=Dv52OMzV-q&1v`5SM%vTog~<;y>P?C}RKyx^=|ciy72J+jS$Aquvmlq0_aieU^`f~^O}ujjZJJV2ri&{DEoANE{Wi7&fn!EPs>UmG~mYYwuahUtYWb}8|=yqC&{wN`-)<yDsWXCl*1dyAnj#j;$G73F4ITlaur6Sh9&%+cFVafLpxt!MjjdmJ<Q+zU^<=g#xqnRdy?_fB1O-wlhV-SNqsd8_8X^Zny1dY@X~`_C`GdTQ;P^OoQC!2737e|5|0FVto}<IZ}uH1{?AsegH|{5yGnae2kM%2(f3zh^y-sQZU+>fe6Rw&An-`uECfUhr1WcbCsKm(3I_?=x55XRMzcteY0Exh-CIU3K*(wPj~CK0B`c(}TJ`-MzkOr`qD(+LrFpT(#GL&-Wd;Y)a2ZlLtMwW5@kFwEboC<eZVt(F5IG+MP)aCj|aX>E(o@mO+UwDNds*wTg2&nqZ@4gvk}yAPCtV#`Sda_k)20a0HeOi<Z)<X{tkq4cz~LDS!IYCG+M#^!C5rc<uF<XU>}bo3l^ddB;uK8o(P1AbD-G1WI59=rm3OQ1xAOWdNqOgJtM8o?xt#`v15Xi0~8m@FRbH{<*h5+%azZO4ks((q{NI!!7Gps2VPYvvmwOmNZPzpawhGbdC&movc4oRk7NaQq~2)kF803SdaFO0i#B3x$CYc{C4Q@A&Fg#O~bc~4c{KtF=(evrkrx%#aEm*^B=!|ebyC=?!R{VtQ!{3yl?3P3)emJ?zc~_>V5W`-Y38Ne!=<=7c9ST-Y37m@6COtz1VZ_3&B0l8?#?F=D+4X_kr`yl4Q~6ovXj<+3<ZAnqa+Mbaedief`_@m9IXltbMn-=6QF`<Mz6T{nazfRWp^fv(0rgymixpHMe?et`0xHAYOh}dC^Jrj}EVXykFZ#dv+}PQTL+VJC^T0;ETz_mQU$iGNtRCJ=<T{y}|jhX}k}klw1Ybr^b_+GxKK*Ok-xU(Dk$uS%78Zx|lO%s;I)03VxuD8$aa8qYk{`#>=06`ib}6d+U{#pZ~`{Za@9BW4GOAd|MO9qM)n5drMIulE_XXzz{w~pi~9*87w7ooP)_L;FBpWfgN$k5U}>jS5<ZBMq{p<|H2jrpA>YBw98F9scTLmyozr69RK3t;v!e5VLqOQX_7itmI=qj+ts+@7&F#@<9NU(e9$?YNqcwCkg?kwa^`l2o)maa)3@uf*NnZ2Lt$S_t2)|<j$!+3cf^@Lz2=7Vo}6>-ClBAW@`0OH%>C=qnX?u@v~c<Sch*0#y7%d?d!PUA`=>X2ykON+4}Ny}?0+9I`>iczztWuZx;OU?ZT`Q^h3{2g`lR~7=Z(c*RKNId^SkdFy(u$?$F|<@8sDw2ZdehleLq<9vbSb|{rOC>^d4i`G-K60_S$>hHTQdK?g_s5Yh~5dm8BPzKRz@1<oL>mht~dcP}jdFw|%rr+b2791aT#+$z^d#l{lIu8zyibAms?99e9L=UQiH(0$Z&XnNA(Y7&U6hF~=PGw>xiq=U=a`SpMm|@4i0c-oKx5`tjRtGqJ51SY|;}fK-(@u&ZUVypd3WQZ38UK(_jLieCY{#RLujjNfrg&)2ckB4m6qmq~zX6cttF>}&pd^u@PShE4Js-Bw(+qnhEBRSPsO2YV`-*b5FbPe^tY70PlHK)mRd(J@ek&N?hlLlX~FEs*Z$p9cz#%GLJnVS_i>ZTq9o9z1cY&@NT{AacE099Dd{8T)NflsI~1E0L`><7ncD%?{rE`14M@^{;<;Y1Y+C9-O*-&ee<Wx#|7sGd`O0<f{4aee=YM-e))TzW9Cb3*W7N^2?X!FTeBQkI#JM{p}ulv-^S9q6c4(9)820|1W#t``*hRCI4AcS+S<F?rYG=nUmL1PwQ=b|84W@b&U<5Rla;D_~Kc2&3t?9{Vtf^%kI@y%+OZc<*b?(uDLf^{&#=%P07+f#-IGU`td1E*sobB2NyG%X%icY8t7?CHhQyx@%kVReHV5?QDGfPA3U`CpdU}U;V*xF^_3S_EME+^%!3c!^Xs!t-ENzW>s1e!G?+84X@GJR2R<lCQ5-s`Bw<3E15B49CKx!d08Df~1J5_Hd<L_LOcM_Q1Pr>a<&aE=-GGUa8}B~(ylD$ZY<F<AYnYi-%_y<Ms%nGqO*?~`c4)CFN3HG9Z>HF)0k62K?&wt9Q8K{B7X?jIfIVBb?Z+U3lc*NDVNj_x2M(IF>yLLj`qyFEkF5ZBOcFXtAS$5=W@RJr8<E|Nyk-z4wia2%O5k+Xo12f??(n_Ny5N+1ZvFjBbFN)H=lT`1Zdf$?)(`Ky>pyemFP{JQ*H5nOec`{ouYBA4;y2$eT>tKZm9roD^!$h3-SfdWH=6reZPv^7%$GoFYxCcTo_W9WuTLwVuB@*9vi|jVtdqy|hy?!q54CT;DsNa`{_@>;^|S8hk2s&*Yb>2+Fa5i@{BC3EbbHx!f92h9b2V&`i^ebNRP4MmV7Y-*$zA9Mz%s#*gjFgiY9R>CvEzmxe#Al7-7xj(XBNKy!Mkt0{l@)s?mPR}r|!7@#-JlPRzU+y9V3F(h`l5ZC;;LCVZaV?$T@CNfX~9#$2Nt-fN-%O8nc!#afzeGp3IFjDbEnI*-g(hV5cQ#-gNh_N1mMw8XGja6)O^6VmMLSs#FJ(^bE_#v@T5S#5SiOP>Lly&|Rb1*lv{mO8qWiCu0T+5HAHcK-hb>8z!J=P1tJZ<9;(@%k6wci+xxL50nEqK&3A`b}eu!o>ldoW*D}`K}RKQMsCeBV!Kpzoe`bGc9^u=(fgcz@z3wO^U^nGU%ll1>z2*9_T!m1|7Z4$4<A~%_{k5~J-w#)g|B;G{=WD5ufJcoe(Azhk1qJ+y7})P_0U`6XTMUN`I0&7#nMBsnh(EWFMOx`@`u%bEs2+W-uU9H=-cliB5l^wKr>Ii{UQ2#eR;#u>bm#J>z<F6&$E`y7N1QQz>Bay28vJH<QSqCc*r<m?ZHkgf|crr`j~Npe|ppbH~i)D=bnG;ga5qo>g&(keb24GJo9+4W!l?(+bWo%=sJ2i2@;GwQc%ltd@w6fu%cbVyf>AhR+^WDXkzY}$-EcI)5a8ESZ3hUoW+fmK^7)P8U{uNfq3^m^5ipbncg{Jd#|m_PMW#{;D+2@8y#+{Rnjm~9o?<eH-J)@DTx;#R=6D>CJJ&D8-}T{M>psZE^aPNi?cm1j_Tdz0UM3l?!Y~cKRs+TeW3+lL%BA93rFnQmB0f+#z)Vu`d%Xn+LExnT<(CQQtqrpm7th7Y9k0ob`RQZt9?#6?82$%JT(294<Gr<iidAnI``&}XW#t(jA<XvS+IEiJ8Pf({D-Ih+xz?vy)X9m{&W4Bg)3j5_sMM!esIFvx3{1B`oLMQ1oyvY&V9{!;8kn>YvrfjuD<$l^ue-Z`P$}s5ZvE0&?viq=&gMR2dHXaHa9G*m1|X4R3y?cK+fsd$fWh6=b0l$3_SS9Q>Om;;>R9;<juEUdG^_-ZomE36Hhv3^DQRU8ZqYLsYTBg<v6G&QKg*3QRsVti;Au#4?@$XgcRTj{1o#O3<^)fL4Cl|Bpi`;RrN68L<oLLIsmrn1zOj2tv+zrAMgF=)`y;v44fF$2bg{ZC|4D(nx%)8G!U$aEPBoXQ^hQ$T`NKJcgTTea4L~TW#IJrmI|<9Z_W_glDHI0joZTJ;EqvS?tc7l#_x5op(p_?lw|_Afn!Im1qwerMxLG6cG<Ookm0CDeiKlxB<<Cts~LCJgYJ6R9((mjRD8X&7Ec^CYTsRtIQzt_Z~Nmjb8q@|-d~r@y<zeF*M2znFYnEn_U^-vEne{U7f&t!=DBZrU-%y3e(Jv)7Or~#v8B`Ie|XxwclMg|=HOYc`S-u9&3(za|JC@RH_MN|Q+e)#+MA2wPgYb{udRObbse4L<U9Sox7yy(L?aawzEm#|gNAfY-g}qxFZk888FxML&js@yd*H^KuRi{SpKiR#xG-{66-#Y^;U?uc1~>uG0CY}LJb_^G(Fb7(MvTDBA|wXF4vCS{MX3j-$)!9TVs?s}klj%LO<>@ZlVInA%UCpkxy^Q=sGe})6(?W)_r^wB`fWWTsHmVVBTSA;iZNx|x&SdC3oP346P0@}l(bUGR1}xI<!B#aI&NCuM0e!{rWXl2GOY;vubQw+D}J@BGI+%B?GD`Q=NHvG2HUy@tjc$QeZ!*}IKXK15P-HZXj}2%4NfKWsu2eDKpCqiNuvyKJMBr(k@%ezue0KGRqbl1)FNv@NBb6&wmR~lGcWti^gFM7Y2NLhJbK6S2X0w(-*xZZd)*sz?tW{*lgk#ox#p>5-#+~n>Six~*Za>6-#)qelP6ZppSS3ux$o`&;9H~TzR^ARwdjG@thulGvtM@RzUn{vcJ<j0lD8ID7OkqT-O%3IT^%y4bI-{;p8m^|uDbrpf6VyD?f<y*qDwD5_>ld_jvp1rUa3?lDJ9H@0T_XA!%I=@VMHp#Y(-2ff&aVIm=<#kKx7M>lYa#@`r=d*w2jlMnXI(gz&vM;8Vg}@ZH`NoJ9g$>bja_7?dD(!3#G#Nt#`b5#)6G@JJ|0WWQ7qm>UT7Yb0dQylBdHVElv2Q12kAEaxW2;qgO7riUoG;U<^e8jZ1R~WlZe@eax@|VFzjUxaEa$J#O!*jhV2+;lJMT;8U@ytb<W$2R06B{=#!9i_tbC7gR4W?Q9_JS`t-bIKp!1lmojKdW{g2v7i};jWBFalCDa*s}l7z!j7`lNbL4{G-BxRU3Qpq(vcTl{rd-IT=UjLH-0+rrj?J}v|{=dZ_l{ujoE+u_e1kPdi3p;3zvU`Sbx*|($~Gut^Z-+s>KVIJ^RQ<SI>X<ga_W*`u^7j-~V#_z$?M57m_(I#}B{OSn%e6JN|yl?SH@dn(MDP^H)FLd&-p2V@3y|U&6kcif$Odut6UJ<S>cCLB>THwkRL5PbsEezz>Gi@HlV8#H0~lr=&6F&X^9I<~KSrv?NO=v#JC^jJnkxIcwGEP+Jmop$OEvtPAg+^^@OSS0A~#UGEfL2*eBE0?L{d6jU17fF4v2^s6Fh`PkG5#IZw-7B%X%Xp&8ohO;%@!4B<deGO2w4-ng442qWHf;|)kQ6+32Q0^W+eCq=ayWoaFqc_nt5qd5<&~4BZEjW;GIU#W`<XfP109OMIB#we4^vZ#kcupDfG`t$13`8BHm~O^FdnN2{B;CzQcU#=mmUJ|tdewjnM)!=}Ys&-AJo@q*|M1AH8{dEQwv~@w|LL47Kb(H~JJYXzebycCJu-jMg11&ZvE=J#zUY1SzrFwbZ|{>EdKa$!;)#`SEm-`Ihdw-O=9}BkdVQk@-e{Zqs<Y1l`wkj5$nt@qA)s*MnE!z;g%A^N(S?hu7v*GPK4g{!=UE<R+j7rR><sS(j^n4g6Pm_^so-uBZazm{Hc*u(nf%4FJlV&OgHZG?RChqFI{4_5E?@A<xIK<24;lkDFX&X*fE_5;3^dE92?!SRXTX;-g&d$q9Fd^$-~gM#*=X$o$~v~)=HLj%Akbnm@KIRsLt@*BOfzu(#Hlor>cHlRO?N)wf&)+gg9xf{bHExb!v+?GSyEs!V=7Gu&k1o%oj^y8=Y*i8Iv}P!5ZrJ8jeDkmr}ZcRtbv&~62Gk$H!4v_EgsNb?&+uj)*Th6;wp)wbX9Acjo$j;$tV8ylv{4S<eAym{d?XmA3t=%Co}*2-i)bl%((WI8TY(9=aEn6y|U_wPd6<5;)iFy>V0lQ??1olUAX4U$Ckgn;In(?{`(>~3Ke0vn5z>ykq5V^+rYcrl3`NUdafnmSRuxeRE4r71=dQKZivnV-GUR??YQk7SQBi}B&bWCFw&+3X|IXQ)t|Khl}XWD-VU7H<aDg8gOCquvkCi3)9W2wH$48_K4<;8IeMG0doZZY!i`l-0uMDSw1Wf)8KAV_MFX{H#lZO&!U-_-2wMXND5)`Vmq+$kI?%p`{R9l%Gjt!Gg1j~z*wuk$MK&r;iQ^`=7kWv1(ldDYRtKGY?R}f<v2U?h2w^h=4~N?|uzfS;6p>YhJKO>#ANC{A3EF}Va%?96+Zz518^FS}Sonh2b0~#UB%xJ}!bX&IR?F?Raz{Pttd-lMN=F=aCQ)Z425Y<?Sp%E3ttV`M+(BnwcIKV;OnvduTRwf{`VSwv=Hr={y*KT$H}1ab&3pd(!Q6*GedLwpkAC>yg{#n=^6b~W|NOeQ+=PYlOklhgx`}9@4>g_3CDCc9qHxh!pB6w=PUlfY4y-Nq*#pXjeIgsk0|yY)T{F!9$(0c)8a6`6wduCFR2HklV1sdM8XRPUd>)AR_zN%j{p=^k?D5lh(0ISC+p9GVEV_w+at$Z8ysBX*Xd;=uaI3mgDOsWJMmqHqgKeOI9&QIk!QJ~k5Z0z!6HbD|7tpr@+$n*l!iiu@*dClzov3L=Wh<y#ac9&yykq2MJ0APnldk%kSMw=N86F+j*}8^Bi%7>#1TUh6-~zMuG21mj`w-0tAbFc&Ert#P8g>TgW+7?dA!ub$Sc!Z%s!?1CK`RR@p<7G*W;trFlzZy+!5!`0^>TaS!qF_dqXrJ&b+dg=Jm|NVpFVy16)!z}^MB^u{K*4XzJKqfuTH!CrRi6_a_`^Ye{jK)N8VU7|Ks&Zt(oS-Qzbb1^s@d)vX`=~A<CZ+zSM8cLZwI-m~3fzKm~SISVSq%I9kX~Tenfce%26J=Z4s_@>dQFlBGsq%fNmw6p9;7+T^c~y)fnM%ZF}vKy}DOzkQff>$IY}6SX-}yXn`guxf@CEr_+KVkAww-fdTFUcG6@Rl`lJr~-!>mW?10Q4MR&!m@x@;ICmMqQovYtfT^mQ*Hy!V1;EjY5Mi9pxGJK2UI#o)CY}g44p7(^3iABI)B&0k0}-kHaga9VSt?g;6?&#f-Qsofi6mRglmwK&Lj)p0$zqi3kEQ7%tr!<ec+wwAxNUAl7vYdlp`!SNCGzr-E!=c1|BvOKsg4Y?x>c#8nteq?j!)6yqVZ-m3X7U8|}XBLBBZq(i_izbjDS$KYIHokKFX12d2I=<I>me`QxkiUh#TdZ7S&52(XPU_s$~qL#Kpf+3NFu+jR5z3<JC9(2x-%VeZ1@v-Xm18vu)n1a+#ykog|mQ-x8^CJm)cS<`bGZG)|7Z0FXw^Y428-D9WzZOYI7FlnD-N9}s}psn`m+IYwAi92;o*s(Es>-y*|+Qx0wHgb#3vD-8@+Ny2rHk}i<?V7l4ZR94k;ghPvCM1K$BtymqJ)`2DaY@g(+K`FW!4t{@$CL+-t__*c7`AzN*tqiW36<fKD#JGpyGF(XMwN$*YmD5YWAwHi<F@bFWcMLkPnopOamW1W?&}_TcHqz<r9u(RISq?{K@tZb05Bn&ih*(H0{ue^LXc{R_Jcrt>Cq&?9ih7bEXn}vOy6_MNd!hGfFAgE6p)e@1@&@L4TD-7G^<IY5`*Oh1{W!2wVr09yBanEqw1<PPwy<(HXXJ3p+7q5oRhD)^-l}t-1PPX*ME5b6(0e<AZ^jQv|8N`x$gnDtL@hhUsfM*Mg+CHxA2iVtfB~`mM_?K2KlomyU0>ct(NkfH385{s>&^Bs86!P;3B>T4xj<fyx);WKEG_`jq{%V{k`*kb@Qy_uDt8e3vWB{oNM+z{SQ-4yJ*Vk7f=5AAND@&l08njXz$Z6JNVqI_x<%1`~7C>zQ3IM<8!Xw>*p8j{fpo3c+{D@9Q&(1PCRF)V}7~aQNP^dlnZt{>G!)Fe<7UjaO_z-AAjy1CtbYz@#pV)>^VCg`OB>j`}wwq{%qUBPTlFqv-UXQ_dojCCHtH;b^mj(|H-9yoOI)i^X__Z{_?dqKRDL`U0Dd&epDudz8Iok6VbHn)ccAj76q40OgF~zD6B>B=^wg%(c}!{IL3y8=rzO`OBlFm=bJFBz~6iy=(?K3)i|ytaV2trdzS;J7K1h()gz$pq_b9OuZN9_+bBEL*zW1*+Gf+8k2&y{zd!v};Lj>xO6gTvT2#`f4=v3h%J&iCrcan&rKIiIE!kRDrM`=*Y3Yum**3PeuyRA1xJ1H8d+Fr5z3J@5qC9!d0Rsg9PzGhhuQck-uC{W$64k0fwdU8FUZpLpcf<`~o*i+sD{OSejjjkDI|tQ=Zd4mGsySk8dBBL~urY1J#?%H4uM8U2Hey1@s7W28#&(UJ)HP<4t}&YpoVZQL=t-SpH|ZI-`GASr4B2?Q!4tO_FmBVH@mq}8a;MST{%FFE`;OXXw=p|TnYjCbn@&DtoBfa6@vsy3IP&BJPCfm!KU~@~Xdrd4qb7x9C!%SOT?esqtceY&JQHaeUGFA41VCE*9+ukJz`$Kf12#R(401fc6tkK=Oy~Ci=m=|f!wB$)$8xz+fujNlV|FBFO9FxW7G^6|qDmZgH0$m4dPk$t-QH}gm+KAK4{q#eRo95C4Q%wm&C0UgWwNq3t=VjeT`smYY4`|_8cFS)lw)%|QFfx1L-f+QfsVo<3@Kq%wt1ORljKFulAG43QZ^>dL(x>42w5oUcu>M;LD32YCGDM9C}J*GK`9nhex&gn3cXmO0A>jjDe*e_uUIS<3#C#KFQd3Mzly;`K2NVL6%++Nlb#l{S5+!p1a_=aD>GgMs`sV-IhKRXF>D@46o9b=5X0eM;(~+D1G1mVwUE}HxMV`R^bf$r2!MxiwlMU|z?rL<_yB-|Sq)|vJi<|}MAdQ>M_#oYV#qb}nhl_aat$D^m%BUa&2j+va*KG`w<q6oIBnA;J56cW+JeRowla3|?NicBOM~km%(O*@?WOv2hHsh%pO!C~TH2}tBfd)7=AE0%r4v;Q!_zSV1Na8mZfON{emoGBFxxnL&J-oXP=ruzP@CbYsZb$mQB!D-fI$;z2AaA&@ka-}+Vn8?gp=u9fejo21FJQ`fZ|?8z;>{357?UKIMl8gBV0V8gA2^1O^2Z_X3Y)_vJn)nKnuVFs>BQict$y7m~s?^fIEhA0*tHy^>UIwx&{$w(8KZXK21?b62RQ015U88H;TgqwK8&~#9<lmjlD(#?4fG47T4-YM@O?<2Gy;h&~z2<g_y@zNvCwBJ@K@(OBF`gxqp72ek_WS8<vr#%c3OB)hx>z|1{@ENW#aS+iAsUTIlU!{|(`*nw=$+zy$_<np4VVB&BUb_y#m?*KhJvEYJ@@SkMF(ZiJ{HP2(*&^c2US6g3Ugyos^EuHZ)2DjKye<&l9}<ZCKvOccCCSPkkJkX6RXmPa(;m23*?+l~!jv0xJm8wG~Q9P+_hs7{03<O4enebC#n78@jRWM$13;8Nhxn684=2%ug^VGzT4NW9v|euEJgp1=Vd97Q&oq(PMUjb;TXw^~cewXg<2ceEw7YLqnC^OH6v%G##M0Rb`{nk-x|8{}$HziXAJkbr(w>Vt2qw>Gsww(>oZ(%Mql;yY_}sbsC)c`5-mZNUC}4h?7k!~>PGr>H=N))qj)u8$5i))q8>3KSlZwaY^$g99iP>QGw3EIVra%Og~D%KUVQX>cGC07!dq=~$J6qwaL-#-r2ZS%aS9D^$cmNm~}VWzslx=2r*C8)cJWZ7hc)FT7!<eFnG|43mUiX3IdeTy%xeaE#6%h5NV-kb?&xfq{v87(GWPp&x)U=Hn%v?O_Q@1fLg|qofih6?iOHs?~BODpx^qZmYI;MM<57teWd9o^N`Yuli*4Taz+WR=P|c5z<OiR7Jnm3Z-l;MQc<_*7+wbH&%3-1?+GGTkgfD5KHGQz9J6ib(Az7fvO#K$AWLik<FPhz-=Ruw`iK9WP@^K(XmE(+T55OQ^<0|g43K{-6W+E?HrmysLLi!*k8dycMUqysiO-uX}9|guF3{#cr*_y?I6M3B)CwQQ1&Q@#?!`71T(&<k2x-v<Wq){p#2aqX(Ox-H_vggxdUthKXQFw?_L-KGYA0Fay2PeD*;Z$iIZ9_NGfoY43m00v?f8b_esMp(|(?{awCWmk7Z2lBW%#eL7#jRq<r5|uJP~JB}wl)@U)PP56+h!D{`nMY%Qu@XW6Z#qZY`5RxFMI@vu=UL1p-?Y_N`z8)GDgIHdhQ<&YhoLZ#D?S(OqFfI?}Mm6>mW!h;n+8RS-Gl<Y0oaOj6J^5op;6C>+mhOFD926&iI;A5$0fJJ|(gSlx1x9Rwn;~1&87UVV7`C?;t*XQ6V>@?4dsWKFcfU(*r0o^*P)XMM}Bw<{wRO&Tg^kKPzojSb4a^q}JS~>>0AF?Sg1+lB!e1I&YG;$s{VE=E2!&drbHa$U=^pe#StK52B?K7=175$tt1Um<4*#xbL%3BoX7#yvTh8qsrphKsLa=7d?-_|q?SGF+C=ro;s)pwQzH3LpT#3syq^W6U=bBWUsI_mz5IvDq55+Xm3tY1GI%-^FjOi8N(Qx||yXl6RdhQuym2l(0nR(j%iUksqzJi47+Ac@Qn=4S7@?s6`ojj<r$(=la+yC8@`nFcjFE+;_Taia}1MmtEbX`vTkk#*MTR43O{zA+KkajRLUCg77o1iJ3ZNKiVlT}iu1V-7s>L#t50;%<t)qGDWBt(><+=f;(3#}9)$CgA|(lERsOG^|9h$WDi4OPRv$@6t}c+3@#t1bjBWu-|~HemzckzC7<V)FE{%E1_!5*^#5i<c>vyPLn;FS}`xf3TXtq&)sWv;?=}dTkSFolRLU&l{2zsj3Hy;HYn95jaK)fh_ZlP%!@!t>~Z=ioa7oFB3<LIpufWwK&2X!!(61_MkTBz5y<6cJK$@1q2ovC=rmFV^8=CPP$xY_HtWcN%LNPKN@sOCx5&U67GkZ$AwfhcK))KdO2a`yx|8p9sc>a+I*Oh89Ae&-O(V<%mA9DG9gBMsx~(}8G}&2xHRs{TF)Q2<wV(e@DhX2ZQuJS_%&BzghE1LA5?|TlH$P2Sw$5v{DHF_)VTnw1>1X86@|rWym{H@o!>RkAH6_@L0uc+j9-nJ?X%9HE&lMlp-oPE@klBp6ZZ5KDkiR5+0oH2VtinmT(Zq3e*l5d?ZK%~gO$c)vUhC8U3NtHI&R)~yf^ZE>DeVMqa3whG0X0>UEy_Rd>-NmgkH(?{_;5hn)zY!is4(LIblYY6rES2eRzfxn$fkbu8D*6pmejAcOP{VUnZ8H!vrxXvdy{?FCDyVBa@JbJ%y;mHJERc_SRWyq#?YUb*>bY6o8pUUgh0d|jT^(T1lHiQK8?Y2N}R|t68T;H32CMiPOt*yD#n6+7ws&77^pa|#z|YX(ox5gS`CE^_UAEWgVX%prZ$OQtE!jwIk#~rDk?QVh6PmQ(jkpg-v**bG)pxN@kPZ(r}8Dxd{isnyq!CHFpK6M5!g?_NPVGX|2ot`LSVVE)|$;x%=Lfh-#WgpCcwRL^DW<5k>+VB>G(EOuBauoBJz1Aa<DHGZ<cuA(okAQ(``xAXsl6cu5eIU<wm}AAUYsM85dTT2x9bGk{||a$FZZ(@&lB+@QUTbr(q5ZW}Z6Oq0VwRIn8QyCIqI9t`eYMtcnd{u#?d!jsvd}2GuyKL{Yt_V93?i3^%VKq}|$S_K=pTScc_g^3me%WS9>FZxn&5yF4sI6TWWw3MZy!IU78KhMFjQEuN5(Fp0C4f18XN%w?6MTTp+7J);ofIDg8J-j!62XKcAxl#`n>Z@H@W9WX7B=V%U(MWgvy8m3mJ>NF2$H`R=IIR}h8s;MlaF}^0GuSUsI7x*_)qhMs8l=BJ3vW5e=uxT?5Ji->Q0+7z=*Ttl36pLW^Vu%*8qwGY=BXub0RPZ^L0b%xH2yX#c^FypCdkPsfyc^VMJ8*mu#N`l<xY?;tr)Ax8q(de@(46Z=HMT=B6`Y#8nobdHL(YB_pi9I6tAgsT!+}CB93UT*(;A?l$eD~H-z7NhdYwLH6UNlEwCxg2?O`dv4sc6)ywj!uS+{E0wwl2uf~Dr_edf6U2ezmv*rXAb>2}J53y;^Zat(s$>(Ca{GlK%hpS5}ok@rK=1u;NFCuWE!phE=|7KdgSdcu!%tiEv!60E5$jO-B^FS$e<F3+KELhRnO2~C><4?cFda>A^OEcdT-z~}|$3|DebLI;#AZ0=nK<H)Zx6wE-d4X4$BTFIsxq;f6m?MyoswHj__SkyUJ9P}ku2a6t&^=ROrO#;+Wv2-h)^GHKo<#^u~-6<4A$hCL2a)W&-HHacg8N+mlE7}T8eC{{xG*74K(Ngt%Q&VY40r3jqvjbTr=L~nDXY-cl&B<gxZjD&tnH#CeV^T+IkKJ78lgS#|qeDz*!gtBN=?dz}W&%?UJ>iAA8)~RKp&%wlrh^JFjiDq#k35;)WiwGz$|6N2FmDl<Z<*<xP!3S6y4)p+`hS6;6j0o$Tmf*CYAvqTf-2S@VT1HE!`zkXsH9&mFid?}=$W@j{2^J9J`CEjMIH6MlIF6F12Ra%ob${QOy^&dw?Sb~FXeTxtmm17>6|I1ada{uAsh6)S$k?w)l`+Go+TxS#J7*pEx26Hl=@FL7ZT?Mqj!t+LvFn;Cs(o^t>oJ4rL$3Jk`cFsB>L6KqnnLU(9)SEWDp73gbofq!Vbo0McEhv1d}$vJPPVf$GS9XTs9j`%xnXK80`h}X@uzE#EL7+#SS?!UEq;NE1<}uhh^^6HV5|tMJ_xa{TqH9#I<r#uY}Z}L8IXv05Oswrv3A5M?uoW=7N0|H<`zhTH6U9GZis0)yBFl!`ICaUQvLMEuYd>TZ2uNthZ8$M=<l~SkBo)h0Vw&3^G?Vii$#UAHfVEb)S-c)lYo%Q<!Db+DzYb<e2IHUbU38MK-qEmcxRxxd2XXkTiGea_F~P`Cg!yZHVo8JxWt?SY1KV7Sx6ac(o17>l^45#QbR*48id)=HxbsT8F$<obQy{V$?s%!B8^w-p3~G7WD>0M~6>>*rj|g4~4TI+Cg9jfnSbXtdpyin^mme2l2|&&`htWm`rza2$8US*^EvO$H}^{m<$cQ&aJ;qPC(@t5M@`IN)|QHDI287!??LgxRwg{)TG7YdNoZU08%x;lHxL=)Ie5w=HUM*%>QfqXu6r7o>R(=fXTaSvKf@Rq<z`8IzI#?-BFlXjcF=afygs%GFK{l>@6>lGqvT6s&pHGoW;LV-3_S3*yt6^WJ}NLbl9q8)0llG(sssa5<ZSJ!v2gv(3qNu;Cf*q9E=`C<%FWhpnm&K966v$SE_NX;l&~M=f}(nlC4~mMfj#EQWovBqAsL~n(O6`JSq!A*yM5)GWwI+FGe~iOOAMuGb?c&vLS1vs5snTixwGVB9@t8mJY5M>=v8V08QBa$X3Zsoz6zu=`1nH9j)g_NaV|2q$V$?5au^Y-ZzqN2J+05Fc}GfOBDl*x!B~;0LwRX=ce<ja9S(d?39O3SEjvTu@^4Jqq9;h_C3m)EH=8CetED0K#8qFOzdQW%_RKTjS@Quy*Tod$N|%+QniA>1}R-l!b;6ASG^>RDs^rZi<8SpDI$n%Fk~q5h1CbC?N9X8>SZTjFGZL|jGD8<Rn<jiyyWu-0xV%YCYe|C_Phs)1Gt>pLC$BvY+uvdRD)6tPzQi(7S*&pW-B~RjI^ac=Z4~CR+5&vqg6#qXUX-G)cL^y((@);<FY=GZ$6*-%ykuatdI>?vDGckKJbVh)4ozPD9~X?CHv}CqH7)L7yUW#)4+ySD58WkOR1KWjOx%ypJ5HOe=IfauWI6aEiCEsgc~>!P-_S@Ylgs<%fOSpB#!Hqs0#R2qFUKcYFGhnm_-5i?5ODgarjt|l+0{235Cn)u$9)~P$4ZV&o=#Pll_+L?BaG<Danvap;!WIRLu?M7U`IEjLA}xj&A3?5IAz0{li&uNZJ)ddI+T}Qjt?BGu4{xBcuP2yS|zjdo?A#rM{EVc#a_pAiz<PBk<(J0V;uqbrzu3dLf)>G6tG;$xgLvoLG@g^d<pKgii(RXqjTqT!#mI8@Tu;1&%X0f)Oj72eRmyFVx`P|2EoOPPs-YJ75r1ftJDk^<wNy8kB*wt0nYN;A9G9BcMN9lq931VRUxJwptF-K`qPDsoXRY%4M%3Ag-~wkz2Ri!1O*|M7dVfu*J+z1C-vg)-Wat7UX9zm2zO^flDV>@?>Yl`2P*<>i0%=R`b_Mn_bP#BS_~k_HCS-<}jda4O!O64y$<wFDuyTB47-{li_axoHi=sCZVnoz=Wy1UC>+(j-gW;jGpDg=raCD?r1l_*5x#f4z1s)jNQu}hbD(6UWE9vlZxoqrsxdzKH~H$nsB7`nVvwczcILj8{6cX9TM4C^~1H9tgrT4QuZX{RKb!Vr%Yyo&&vFqnp|+XlCbi5ZHmJI`N_h0=A7rZ{iLeo&;8;@5@k6XkyR}AXSNhS%Jk5)dGs<r2aQTxXP<n|mM-jm)7hktP9_8Juneh&sifTE<R%mOFh++#2nc4~4r{rbkkH34H|%Vz6;?e77YER|VGJi0PX49lz~xF<X{an&uo(p=E)sltIt8Po6tNv}YXAya_t<v`ugUbWtjDZL7LAl{NEGRS=5!E}$oyCNrqCEe!~xl=S|}FsGY#`;ds54lz~#Noa%NLXgT$_t9IVA69oZY@S4-B^x)U{@xNBr%kqKp$vjI&Ge8@lp@lQiFFyBMY_U$*{oUCJ8&e4!_Qh=qGFon-$JsIQsmcSWM=@3be+Q;c+R%oi;`ZS#VZL`n^qZzQaSb<k@Faj9Lt`m5qVmGLtjKjJ?>RaYGJG&)KuDPSR=eeY*lHN+1;-S(!O`F<8vn8uzo@z!i8g-szLMRZO_N8%EI*RkOnP;SuQ8TYD<YvW6)|#Q2`XmblHOIQsoWNEd5oQ9UsessEhdB&jL<QsAw5>H{4IMJ%r9=m2I!Pq8e+@o?t**;qshobGWnGD6+|aPBOzY;dAe`dFaduMGKvhPtxJ4wV)1Z?F2Tho2$;iIT$&cFr6m7WJ!jYOfdN`5EV+N1shjA@G!d`Y3B@eUUT%CLtmTbJAnJwuI7un2^{z`U)Vik)b&)e0U9bL@i9lN6`0;Q%P=J4%@os^aQl=wp*4lMtaUQkf!6;0YfQjuuYP?R`rBW)vq{%Y1S(&^i_)Y2(kMCaka?CK#W4~|+>(#Uw4J|u@48zP;?m6;xbdN0etf;g{I=OhY@oPrvIL%s|fh|$f80w^gChbdt(7bBt(P0`pgpwrj}5sYpS*9jwR^i9zv4_p3(pmfpvGKc#-OFv{fNS$j{ELY9Ufl>xyet@YQNX?Y17;aIax)lY-khS8oWDuq4?)mwKCG_fp{tTj7@^d)_I3?cP>ymN{xfe6>t;vgX5eGF*k1wih^^mq>(IhpVd&o1mh026Xh90|}bAhMSKf{%+>;zyhbc(OQp<POr6hT*V4V}&<>YReYOPAJYU|J^4x+2#)ttXBb(Gg#ACsK(44?9B#l%0-_<*~n*l@Y`=?H8cL$-gEFVl=N1Uq1-K*pFjOB!&++T$!HA=4#&5Eom+Ph8)Ae>2|3bN==6u5qYAMidtT1eQZo}b8&7!UJJq~vt<#)qS%M=vO`!W!%CO=7<7S=e}z6rids!_@{F97B5oc$@-8f@>_%rVF=vg{KO7%`t_-q#l~h10=`b~`HLf&6iZ(y>?csa|IdVcqB?w>L%A$&NG4>E(Cnt_Jpy7!Y&#uD64-l!$8931qwQJC;y}$qyj8h*?tdGFqB0RCqbTAb@45L~_0K}9G;9$f*=K0Q?$fUqcQu+;!I7YXmQ&Q7>3~JS$4hodpz#yYIU0$w{2b)*P`V6xvii|gtlGu1E9b8CVj09{0u#u@bhL*R6GSn21hOqdBl9Iuv5=?rI-wHZNbmFj4K%bdB+DF-^p}V6{ROlW|$`aI-oD~CP%NM7aLYnk((P(456XSm-7aQcPqgHrS1)pUYrWKK-V;gLJD5}{SicJ%ZF<TqOIM5W(g+b%J1h!`7;H-`zc{Gts5UxP5<gx}03Ue>1g@SE!Sp+*nkRjs;Q5;HW{lBWNWd&jw1on|^!-i4{`~Tm%&ch~!97`{1GCJy9H-)?dKmX!re=Nng+oCOJtdHRh715xeBQ3ZeLm+9bZLR`=?nm+Pv^FKSMpINBA!E*H<yxD}OvA)=!JVn5<rgr{xR%{3OCk#GofAV<JielJoAB^>mme_3_;oAYc1#@cD|geEk}p@LS(0QikLf>rhR;CLnH`b=$%>0<T%!9pgEu6*-rf?X=13jyt3vk%yyTpY7-!CTv45{y-x=~=(CPkORE_Rn7rUjtVCC#>rj;>>9Vu{}Kf3%Tb^'  # Filled by the pack builder; compressed RGB pixels, 160 by 90.


def distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def inside(x, y, vertices):
    signs = []
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        signs.append((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))
    return min(signs) >= 0 or max(signs) <= 0


def field(x, y, style, scale):
    edge = min(distance(x, y, A, B), distance(x, y, A, C), distance(x, y, B, C))
    line = distance(x, y, (0, 215), ENTRY)
    strength = max(0, 1-edge/(scale*0.70)) * 0.85
    strength = max(strength, max(0, 1-line/(scale*0.72)))
    rgb = (200, 225, 235)
    if line < scale*0.72:
        rgb = (255, 252, 229)
    # Light spreads inside the glass before leaving the right face.
    if inside(x, y, [ENTRY, TOP, BOTTOM]):
        strength = max(strength, 0.12 + 0.22*(x-273)/102)
    if inside(x, y, [TOP, (640, 180), (640, 240), BOTTOM]):
        upper = 131+(x-355)*49/285
        lower = 169+(x-375)*71/265
        fraction = max(0, min(0.9999, (y-upper)/(lower-upper)))
        band = int(fraction*6)
        rgb = COLORS[band]
        if style == 'outline':
            ray_y = upper+(lower-upper)*(band+0.5)/6
            strength = max(strength, max(0, 1-abs(y-ray_y)/(scale*0.28))*0.90)
        else:
            strength = [0.35, 0.47, 0.60, 0.72, 0.84, 0.96][band]
    return strength, rgb


def render(style, width, height):
    if style != 'texture':
        return geometric(style, width, height)
    data = zlib.decompress(base64.b85decode(PHOTO)) if style == 'texture' else None
    result = []
    for row in range(height):
        cells = []
        previous = None
        for col in range(width):
            x, y = (col+0.5)*640/width, (row+0.5)*320/height+20
            if data is not None:
                # Box filtering keeps the narrow white beam visible.
                samples = []
                for oy in (-0.3, 0, 0.3):
                    for ox in (-0.3, 0, 0.3):
                        px = max(0, min(159, int((x+ox*640/width)/4)))
                        py = max(0, min(89, int((y+oy*320/height)/4)))
                        k = (py*160+px)*3
                        r, g, b = data[k:k+3]
                        samples.append(max(r,g,b)*0.55+(r+g+b)/3*0.45)
                value = max(0, (sum(samples)/len(samples)-20)/235)**0.72
                if y > 250:
                    value = 0
                cells.append(RAMP[min(9, round(value*9))])
            else:
                value, rgb = field(x, y, style, 640/width)
                char = RAMP[min(9, round(value*9))]
                if style == 'color' and char != ' ' and rgb != previous:
                    cells.append('\x1b[38;2;%d;%d;%dm' % rgb)
                    previous = rgb
                cells.append(char)
        result.append(''.join(cells).rstrip() + ('\x1b[0m' if style == 'color' else ''))
    return result


def geometric(style, width, height):
    canvas = [[' ']*width for _ in range(height)]
    colors = [[(210,230,240)]*width for _ in range(height)]
    def plot(x, y, char, rgb=(210,230,240)):
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x], colors[y][x] = char, rgb
    def point(p):
        return round(p[0]/640*(width-1)), round((p[1]-20)/320*(height-1))
    def stroke(a, b, char, rgb=(210,230,240)):
        x0,y0=point(a); x1,y1=point(b)
        steps=max(abs(x1-x0),abs(y1-y0),1)
        for i in range(steps+1):
            plot(round(x0+(x1-x0)*i/steps),round(y0+(y1-y0)*i/steps),char,rgb)
    if style != 'outline':
        for row in range(height):
            for col in range(width):
                x,y=col*640/(width-1),row*320/(height-1)+20
                if inside(x,y,[ENTRY,TOP,BOTTOM]):
                    plot(col,row,'.' if x<325 else ':')
                if inside(x,y,[TOP,(640,180),(640,240),BOTTOM]):
                    upper=131+(x-355)*49/285
                    lower=169+(x-375)*71/265
                    band=max(0,min(5,int((y-upper)/(lower-upper)*6)))
                    plot(col,row,':=+*#@'[band],COLORS[band])
    else:
        for i,rgb in enumerate(COLORS):
            t=(i+0.5)/6
            stroke((355+20*t,131+38*t),(640,180+60*t),'-=+*#~'[i],rgb)
        stroke(ENTRY,TOP,'.'); stroke(ENTRY,BOTTOM,'.')
    stroke(A,B,'/');stroke(A,C,'\\');stroke(B,C,'_')
    stroke((0,215),ENTRY,'-',(255,252,229))
    ax,ay=point(A);plot(ax,ay,'^')
    output=[]
    for chars,rgbs in zip(canvas,colors):
        if style!='color':
            output.append(''.join(chars).rstrip())
        else:
            parts=[]; previous=None
            for char,rgb in zip(chars,rgbs):
                if char!=' ' and rgb!=previous:
                    parts.append('\x1b[38;2;%d;%d;%dm'%rgb);previous=rgb
                parts.append(char)
            output.append(''.join(parts).rstrip()+'\x1b[0m')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('style', nargs='?', default='clean', choices=['clean','outline','texture','color'])
    parser.add_argument('--width', type=int, help='Art width in columns; otherwise fit the terminal')
    parser.add_argument('--cell-aspect', type=float, default=2.0, help='Font cell height / width (default: 2)')
    parser.add_argument('--fullscreen', action='store_true', help='Alternate screen; Enter or Ctrl+C exits')
    parser.add_argument('--plain', action='store_true', help='No centring; suitable for redirecting to a file')
    args = parser.parse_args()
    if args.width is not None and not 20 <= args.width <= 600:
        parser.error('--width must be between 20 and 600')
    if not 0.5 <= args.cell_aspect <= 4:
        parser.error('--cell-aspect must be between 0.5 and 4')
    if args.fullscreen and not (sys.stdout.isatty() and sys.stdin.isatty()):
        parser.error('--fullscreen requires an interactive terminal')

    def draw(*_):
        columns, rows = shutil.get_terminal_size((120, 40))
        width = args.width or max(20, min(columns-2, int(max(4, rows-4)*2*args.cell_aspect)))
        if args.fullscreen:
            width = min(width, max(20, columns-2), max(20, int(max(4, rows-2)*2*args.cell_aspect)))
        height = max(5, round(width/2/args.cell_aspect))
        lines = render(args.style, width, height)
        left = 0 if args.plain else max(0, (columns-width)//2)
        top = 0 if args.plain else max(0, (rows-height)//2-1)
        if args.fullscreen:
            sys.stdout.write('\x1b[2J\x1b[H\x1b[40m')
        sys.stdout.write('\n'*top + '\n'.join(' '*left+line for line in lines)+'\n')
        sys.stdout.flush()

    if args.fullscreen:
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[0m\x1b[40m')
        try:
            if hasattr(signal, 'SIGWINCH'):
                signal.signal(signal.SIGWINCH, draw)
            draw()
            input()
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
            sys.stdout.flush()
    else:
        draw()


if __name__ == '__main__':
    main()
