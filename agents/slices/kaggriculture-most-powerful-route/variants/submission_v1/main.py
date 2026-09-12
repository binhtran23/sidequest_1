# SPDX-License-Identifier: Apache-2.0
# Modified 2026-09-12: self-contained Route test v1; three-turn sale window.
# E184: derivative of Moon v37; sale-window changes appended below.
# Historical comments describe their original layers, not the full derivative.
# Modified September 9, 2026 by prvsiyan: lossless single-file packaging only.
# Original policy and all 13 action tapes: yhay81, Shop Router 0909.
# https://www.kaggle.com/code/yhay81/shop-router-0909
# Sell timing / shed projection credit: aurax7 (see original docstring).
# Licensed under Apache License 2.0; full original license below.
# No routing, repair, sale, or liquidation rule has been changed.

"""Shop plans with small, observation-based repairs. Python standard library only.

The 13 complete action tapes live in actions.json. This file contains every rule:
choose a plan after two shops, delay weed-blocked work within the current day,
bring some planned sales forward one turn, and liquidate on the final turn.

Sell timing and shed projection follow aurax7's public Reactive Router:
https://www.kaggle.com/code/aurax7/kaggriculture-reactive-router
The shop-pair routes and worker-local, same-day queues were developed here.
"""

import copy
import json
from collections import deque
import zlib

import base64
import lzma
_INLINE_TAPES = json.loads(zlib.decompress(base64.b85decode(
    'c-ri}OOISxvZXh_zamj%4j3K}1~p?Qy)%hoW)OVHQMza(E}#|!2(7`DW`h2^m|dyL2!DjzvHdMuwomw=)hhN$kMpo?+qT(y{QJNC'
    '@Wa1<|35$c@c;ae|L+e!{Oy1HkN^Dd|Ls5j_CNjk@Bic9KE3<$<!^uf&;R=B|G)Bo|BwIkfBnDyxbUxk`tSeopZ~{y`@f(3$AA6*'
    'egA*|@!LOs|MdCc{kNaK{_WM{|A*Z#+jmd@>FWAl|Kq>DI{s^4wjVzNKa;$ve|!9Y|G%%!zs27kK7aiMd5!fCetY)Ee);fu`?qPY'
    '`r}o+`|ZQ8@Als7PY=5%|FB8_(wASh+fS!{YjG@ndHD8hEFHhMPal5z`?pVrPk8pB9w&g)S3L>v;mgk7?7`#zwQk~X^5D<>`K6Y='
    '+vrmn-sF$pK74%t`}e>6_1lxRAbNlQ%pObM->IAI6p<g_{j`+_<hgAkd2bc(aku^Q_54*oz2l?s@n3GeWMi-BSnhk0mY#oar+20='
    '+wJ?OKl|(U<HK**zI1dIdp^kb74h5GW6!GmFOPh;C+Sf6-L3|{+kW~;Zh`}EF7!=z@4jw7bC*3`i%25+FMoWfrLQe`zrlAD$}qap'
    '!574jH<tLjk0oSr$_d`Z;U+)Du8`WDo8*%GZ9Gl|jr0DKr+fNrofBB_PsWSQB_H8PyJci~Jbsk$JAcvw5M-|Xx@GKZg|}McXUJqJ'
    'a{I_<q};cXWu$9=Mw0IyWReQp?1~Z>x>?8**WS&x{0?X4GndR&Qst(;f;vxC*TPIsITg=nT0wh$mmKoNpYQiSmh3BZ$RWXZ(j$i~'
    '=#Z{2hvZ(a?-kWQd+I9FY%`usgct`LnNrYbUXY#DeaFBI=N0~+wwXl)zt>)Kv+$`>UH;hZ?llW5AL`-b$L&vFfB!Gr&tE@${P4dd'
    'j@7Z7KmCVH_>mlvDf1XdrYB4O^WpmO5ViN{&z~sc$B}y@y}0eWME(r+rE_?RRM8#<carn-frSjmsp!Rqqq+V#6si{&;?0mVd_^GY'
    '-dJ*BcR#8GAL|kTBjxREK@mIKJl-E)W=I5&0h4tvGS%fQg^KX4y@NN>i8@)c<+qpIb&O~2%cr`0s>`S9*MI-(A8s^s%5-DK&Tm{?'
    '5Tu&K4)&E~i%m6?4LE#3^N}4~0}X7$YgM%Jll(oy!z=b7VLC}6jn|S)SmKl7%a>(<y`r#R2FQ(_*AfT*f`X<btT6-hoMAh{K(Pjr'
    '@*HR&gr5GFcc1^~38*>3oD$njnt>brdFC*1W(Gf(rLHJxuL9*P#(}J+pm`445$Z&h4<dERKHMt1!6dh0Xec>7;-D4zNM6Tt(CxJ)'
    'N!uPMy<CwaluwVU;_PognhYsi8)PUb#!JG|>@tL!c~o`XoHb&dLMipzT3lunmr~B5s+#ZvI=DRrrJBF*(xdYWdt*tq9ohC1Ue!I('
    'p@%DHw>_1c$RG-?w0Ng*f<`ou?UH;0oASzN|2DEoD`oYI+T3JXDV)lTV180<;jq#r6tBaQ-zD8MrEF~QGHqV!-djmxrbg4of_B^s'
    'n2xcLTC(T$zyw%o3P~%u!CQg}?7orY^$f2OKSB)-F0U1X%jp3LEatL$NjQ;1IacKG<bq?m)O1bBSKfVAq#PCp-;mY_O!3mnGU5^W'
    '6;x4}euWc_M$iGa<z>$_3zs^Ad1mOhYo4K(Y|ctez_s!{9rMY{thVJ8Hdf7>cuF4TZz`imMFP7|VN)`rtK@r0!5ZBepXkHqXiUD@'
    '6-vA6H&!+G{$d#>J*AQiOJ4%0BR`T#Nz(NhW3j^kUWwGI$tOg+#nLP<f!gp)f-*;-tz>y{y?O!rQaqWC=wvH)tCAK@s@TlzAE?9V'
    'Ec(epsR8tTYKVMxnQi>xt-;hx6Ui7^LJ0x#*=Na8!q@r!^TVgsQ=$;|>2^&t)DkU*$-N0?{4l~Qu=6;y<o)C_<VlB%6Vs9^(fFmW'
    'n-DnJfAEdQbS-vz&kf$%4a;(8x6rdwv70$5u9WRQo0e?se#vFo6{aBcd#r4Z3eyEkcxpOdjvWoj1<^=dsx>}+!5Vn{r|IE3vDt}E'
    '5yxBlU%q~RxBGGX`SU-pnk0#Y(!IIqf(>QID3n!uSia`93LZth2j7zli&!U3DoE0^chNu|JBUA$z=cla@TOC%Uh!G>M*R}o>HT6d'
    'z7?wb8QeR%&$Pt4GwrGRqcwo<)cSbSU%NDahE(5aXq46>S`v%XSzq^8<Ue;}U7en8r=eW=_=6g37)Ar9Z`~=OyZpQDZ7H<aTmCK8'
    '#zw4BEP0#`rEBc*m7Kj-1rv{F8=J<$Ib7B$=X=e(ZpCFeIYB`e5BVpv@g4?HJUl%8m%DOQ&k;qJXKt$E(*&#M%#bC=u~2+y6nD4@'
    '{n+=TS|H@33T~VH19U;O1yfii&U6F7*iBPXS0yu&S>q?I6ov{5qC*|p8>%3+l}zPwIDj9&efaqP_wVoY>o<_wM}EoJ7<S=vJWoD6'
    '(=T~34b~u+WRS>NZlsA2%NNphoo%~Zge3Lnr0(8BKejMMoVwgM06@>69sHQG(ud03JSHGrg6vBL3EE5x_M*sDIykP|yJO#CMJr>6'
    '<XGy?idN?GrL-4SM`B7<GV6};Yzj}E+RFf7gTg68Q%@nN7zQUaHzSjlRH^>R!nLdxv@7|{3fpYq7U?KdS%|0Tym=yNUSmn~s>y~s'
    'm?Y(9bn5yyiaw|W&*nBo_Jz`n9Git+p3MHX`glpsc38Pcv^8B?=5Bgq>|~eFlbRg@#Fx};tAM50=OXu$%?0t?NMLB^0K`82r#D!;'
    '90Ji+oo1eqJ>o1IU!`GB<z^b}>?8~LAYrHY7*_4*VQ;>&%F3dI;M2q*g<ztmysfHjuf_GMN#|o=k64_O<F1k$7Qk@@IFM9s6e{sF'
    'gRSP#2@Ljr08BbvA?^7j1!zT^(4~Uzsg&-D?Sf>xQQAjLt#-8yy>e*=RZWv9!XWZg>w`V|iEGktuG=T8ZqeEeRG@JISBh}_Y;r?~'
    '>EgAlfHO#2=<GMh$ypB9TchKQR_L($<%$%x%epz}#B4w$Aqi$$Q;DpF7ZoTrP~;G!yz<U~ykoz6umZ2tF}|7?$-sUa6xs-{++JIE'
    '(bq*iMoZKUrGQpr;%x<aXV+=&!?rZlR_0K60ieHD;+3w}nqoz?4e2V!JM=Lb3~Xlf$BL#F7UIE^bvd$2S&*q<pET3Wt;%x~VOCpg'
    'auraV3n=yF0bJ461Kh!;%soprXPY{!#ew(oM(@C1h?R*_*_8IKO%^$raCo7KWbw-OeZ1IAl>I0{`Rl{h{;wZC{(Yg^s?uI=OQSLl'
    'p6_ZvIrK2#?hvlSmtVHqPmSeGQwq(b5Hc#Ib1aqo^9!iKh{4B*>l`_y33*d;9VAJo)00=a4TfB<YVWGmlpHJM%gD?(WwAa6R=u8I'
    'B1OiKZwxKQQqGiq5##F~O^XyKiG-3Hq^ge;48gpQ3qH+g+KD<gpo^Sjj1;mGJVL2MaWmc!^ZTKbF@>I(Mvoe0VIZUy(|s=oYCAOw'
    '?s`bb0V8@j-3R}Q!S=H$`8@df(hj<f7HdwWpzCT)6?S3wiJ?V^0z=VsO`Bjll?TQPGz$`+tjV-$hbybfQk>4B?I3n<^k3b}hHLk%'
    '$pOO9l{mPwM3KbN9+7^RlVBTig*wUnhDAXAf72(F#y&hL%1mw;xq4rs?>v%1bB2+Y%`KjhwViVO%eVMi0|NNvF7KulD#p1uHjP|&'
    'x7mJX97SFPo#)2Rm+SZrAW-BIz!`wMBVmVb{d!^Q7>8Q+asp44?uPF~aVUxf&Oyq<3qb4utzDF$K}tmj5%b{DQ(|AbcWV0E2uvch'
    'C&cL=GBj`SDjn*>Ge@6}aEKybw_XG{scoR2z}r990N|a**~CW8se<?d+N~IemMDM=cMG~Ya2ABR(+LXHKN2zrUO+dsC-)-H^?(V|'
    'eYvw1IWuB0Ru%?z!TzsQ_a{rC5(gKl)vq6hPqn!kTl3ZHVd>5rQsv*4vR%?_<fragw4^$+e>#Y-cL60#6P9bKH*`%wt#!N-1KgI-'
    '?|?a=Mp7ugO)(hAtw_4}W|-^1WGSH2-*clJ0FJ4*SeGSLaJgoW?`^RA21_!7V!P1XR7ylb(*Ir}@6E(ASY^-}E#(^4jg{LC^jv{Q'
    'GmF<3mt)eRXJ}v}p62StWOwE446!ObQQf@qP!)`nfQiKGr{UF=D9~L{`WGGiE_EaeB(VR<#hWe}SEnYPKR-Nt*@`ukuX~271;k*v'
    'EXEeNtz8|%qq&S;^SE^R?IoDKm!ZdLp9n;<LY_Vt>iN^d{@u%xWF_QaqzKIRI;F6%PM*_*FyLr=Czb4sA~oR$GYJy%_eXc?g1Gz4'
    '{LUxJfwtP>p+k-@*~>`m1u=?SNocT`BleGy3tOzv{Ia4UoKFnSB}s$Y1G}>A$A{k*`jy2}lwgFIx!EN(^9|nM8tDlfP|^1v|4y@p'
    'peS)HSm@SE-@sxS7t|U<vMM(>qQ2VbXyn#`3M4`aJtEXDroKHs0=q6*KUbUjIF%dfLE*&mP|+q6Y0#Nl@cnD7TSH&cW6S-|`Dx2|'
    '-kJ4=^5)9V1*a+a0~X2k-aSPciM8#BAHRM0`2P2w9wIQwI)VajoxGnolw+dXP;OTfZqfs%&_`YpHnp`3nXU6+P_!UPwWR|2#aP)y'
    'qJPsg!+Q+-^06o<(UAp8?&TJx^RguT&-D7~`@8tY4Jd*+&j7s^=0WB8Q6rAJSLt4Dfc99h>kx~hC3`<=NawJ-)y13uk$G@PdfTED'
    'eH;W9PxT`!BG^fg`<ujK6-F=#k7!4eLrX=1R8*oENK)OK4y1fYlVS(h@|JLIujkFKWGxu%%7DZ_{fQ=#`A9{7jpKcTxEnadlJQed'
    'LM8tsYCsUy4pL{N`u8~ZRjHH7IB&iL?yejC4-<jUZ~Bu^qN`N&z(Oy2ZW&iuw6ce5u6nL!{k}`TCt1!?`?5u~_X&Ubky*o#Ph)|W'
    'D)?Ku&X&k~t)6dc6D>XwwO4K+Map<3+=D>J8u>7yz{He`;E^-bqxk5uI?rU+dh2*p5FN!1=P~WUF1E1i5j-S!v!f^}3;<_JG=M;x'
    'NTH_$TIA>Ek5Iqu{H|T2X%Z7bL>n+ck3kmMTCgh?#Z#bcLlNY<y0j+3s|}jRVhue-p%clP=hsX(1RHqHSJEMdE1OqM<3-ZS?zk*l'
    'rcOdAIGN?zkl=w%=i~}I21R&{pI}(ku(3}n%%+a4Kl(PNJ(ORy0N&&{2EvmwTjb?wJ1k2RU0DhjD<#*2)lNcjiNOZUSdL<)OeUxi'
    'SsK)VkIUh^H_=~9YBRFG#A12}8wkVIq%$aUTD%q)ZF{{~FU;$y3X6)bSo@ZisB3E-R(H@TJK{Ql_~2$sN-{M*G^fwGC<2J{e3Ak6'
    'U&wyDtp}kw3I>h6d1i1Xl~af30EPoI+XE*`tMW}O>HN86MH7?x8ErA;kG3p1jr#*FBT#B)Xc<jf{-`uvO6at2%a4QXhas_g=!mvM'
    'tGT2r)nMb3?^S9CUiG}T$;oX&Mq8y1ZwI@j^_;yfKEJ)Miqm`F^n|Y7LQI_7YIH!$yGl-#kyN48WhMK@sC$6r14?pz?x;axDrgft'
    'w4pk|5=?nz0ipsGdb0K#z<Z$sQkuJmhsWFgO(U${5!l?`-TrmIMTr~@gQ79<k-pOYTf8rqJV7^3k_2D>7gORB);bFXKSH!LaxPl`'
    'bsJS-?oC_>%R#3Csp*|{*$TI6!<h;;UAAJjSlr(^x%4~dx!R!)Y_NrB)^+zE$faHK#=z&{v2Y2VU_0Sye?Wd)w-K@j#PwoPbYX!~'
    'RpfXkRB=nuFiNF{V1tX?Ukt(FTI=ey>E8BH5QbyQJ^_Zc*^ZCu$fs@~ox$lz(;S<ARsSK1__C1J%E8DpC!8Ga3+z0|eN*ba1D!Me'
    '+}sBp9gwe*jG^FX!F@b?@ZEI#zd`oY2CVdO1agLNvJdVr3(GBQ6m#CxS4GucQxe#dyIj2}pQv?NQ#Av;$D!GG7bts~*HcPYbiiXn'
    'T2)q%gDI1cVMU4MhEIstczhW*bs$6W8z}vqy#H93-tfpaD>%q&dGpGZEgR50i~tYxqoWh@;OB!)-&10U?EyOIG!`9Llas!b*Q>zU'
    '_py_VM@fntn4?9fa2Skg$BP{S&zoUhSG3@CKx;IbSs5yPi}p>_q{JH*A4S5$V@_S<e(#6|k5_5(@YvNA%^;}=xC|jxh}LyB_9=C5'
    '%q{SnBaQofUF8TAAswuqv<0|+wJaC_ry@(u=1}uPx1kB(Sq%(Y(4N60TmKXXjbv;z0MS=uibAt0Uu9^KXJyrN&|Y`yK<lgj4C<_{'
    '6&q8hN9Oa5*I*{?NSc<<UkIEeeUv%5C@#8e=c3f-9(_H;8&59Y&c01Zlo*tL=_I0tJ;Jkav!eB^2HPu3xfNW7a<wIExwM!ozlvSj'
    'sDNsq6ljmWU%_Qc5jF{#Vgz_`(WmbU#7~t}Xgeq<SOlSB>*Xn_J3rj*fTHXKi2jWPk00O)oOJg+@#`bLm07emTy_{16MDQ1-v1u-'
    'NP#Q76Y4%*d%ON@JqbrJd)!@Y>Cp|MnmU@ska;_{=}R(;4J6j#0k9gYoH_xOpH)eKDak^Q-IoFYNPv9|o`|tFK`hgt3I;(8NEq>#'
    '_G-8*$M>=w<Jh-LiFH84O>`Sb@h8M=mV=nOHXK3NR@4Afl-yxFa&;0$sS+m?elk+kHI~8AFPNjp^aKwJhgCiNdWG_oO3?8tt3?2U'
    '|7y0Pc0NLZ5{zOHfo2;Mb<7!~oF|+Ag!4qTQw%CM(uNSora{#ItFPnBXb&Koxi{6-oMjyFuUud);Lzor-RL_q{nYCB^MOmJFnp5F'
    'jq^JxJ0?WiHo}R8v4)eA!v&e%u>0q4uO0AMD)V8X3cBrRiQ8;hDCUd;3?gw-&-Icnkp!ZyY|)sAh_Nl5rx)gK4?4W>?LD}Pzq;{('
    'vIP2a2o=5gq;t}RH_&arUN(q-#o?a?3Y9k+UxV$>KQ9DpTxb-_u8M=+-&9YANZnepi#&iWK_O_PI#Q!yL=hft5<z+ZYJHpd5ft~7'
    'tE>&ZQp$GY*zcV9!q>ID5>(1Mvf6d5B?l63Aiq(>Fhe-hde)Tt{`iK*sE+`+jgx=T;c=t*z^OTK$|a)!d`tdCi>`?T#|zAYg&qK;'
    '{wAp~VVY}8BH(f2fLr*&P7Y3-=wu-@(4Ce{6R*yfXce#orIG_b5J1aOv_Y;$J61v591s`Q2rvDLqa{xmlpvMSL;)ERI&7xUb<C8}'
    'H;EpybQV*Bp;@ZtS+JV+wKj5&u+gM1L$|Q!mr`!T>eW{qeh55NFB}sn22(+uHG;5&bquNbjw*HrHPw(jEa#~nTQJ=cSRH8q#crc*'
    'AIFi-sfd|F0@t(hg?*;h43>D$-=YpB*8ZsTT`CYPte2?jV;`hzCP$SUKm3eVwIn-T8H+2i9Fo^(u--#Ed~26UVl-8T7ox?^+Cdu5'
    'N+w-gYzoS>1pylj3iK$=k#So_lh*5ceqtFslIFLd$yCkQHc%tSB%w5?S`I*hllb!W^Sj-T+s~i>@#Np{TVN&X+I5{TBel5UJ1g=i'
    'I^TmK30a$IiBD^Fzd6s<+i-+{Wuc%4z1P~;D1V1X+bq6Y9joQ7d__^*w2>V-H%xKZm!n4C<SB|;VL<?7A@RxAe78^;SXl_Y2s}Bg'
    'Os$*tC`auyyV2NQH+3`yMxj$JD!GTYOJPS_CE3ImD%qJnD%h<Q<SpPB##NWjg4eDs9kO`1JXxT8GEt6F&1?t<a4nm}8T;ik2<bab'
    '%AqaRQU8J>k|T<^^hu$mSRJgmFPU3BOv8BYW#@+FY>w*|a~iF&M%TpVarlx^)Fj%hxyUf7uF@1R;a20R1J(nLskiTS;9bPVBIN6t'
    '0n*pNQO2`@*-xlwslXFX4n!BPZoH@$SU=owZg7kYW7x1G9jy}}svAQno|yTLP;*l!QnkuCYof%8<A*n0!$Ta2-iZBr7kBquEH+?P'
    'cJ}AAJjAHdbA>2DD%x1ENE5o39NawcppAkujIYk<gCEBBU3t&WVoI3Z*iO9ryPhy_bbjIJ+`JlG6L&*Rpsafk8aE{F!QdQb(uv4T'
    'iFL{OZZZ5;PA1LyBN-Z#tbRS3IqjH<DVU~7RYA7j)Y(igq_bh@n8o2Ngdt5vJMc+?|Fpbs(^n#C1AU$T1nLvpxx53{;m<cAn^mlf'
    'iV1Y666b{ms<^5~o+ZYJy6wn13rdZ~{m*V{#}-T9JW&4Z^TO{Et&S5fFY{9ebCg=+(D1X}Hf>6>6J?6U>6mjn6kz)}zoYb)dM+~S'
    '-2rWA=sWEbDh6>&xLIMiH_{bN5(-)NpP#1{db1Y5p-|$Q4wU@3^-XzY<LIW(;>2Rt#O}mQCaDIzi`)Xn1T8YkPSsl>o9Y=`FbPH7'
    'rQfw3Hc2G{d^FTdN@mLyavfW!rc%X?N(IrY*BCX`V&4IV2+HYN2;d&yXa_7*brqU)Xli7>!pHvxrSv=)$;$0D-GeZ+02~5ks3w-O'
    'jW<`Zg*#QcEH}|DRj6~<DR;1PbZE=RvYAL1P?~zxvR#l<Ktr1<21*IrV)6(ajg`BzMVxZ>RMC6qahas#BS%Iw$};L^P-rBeSuv{i'
    '3Tiqg?`#IWP6w^V0dcAlZcLsvd?&AZLMlAdF9$8LM~{~M?mMjA-ITo*Gnhi-p{vseD*s;9kUo$mJ{rjX8r#r}EQ39nLsQLQvN1~a'
    'kB{^=^#{6)5hIwWg0zWPaBr)rg}TP(-V+;%e2v`^$-gP|Ee+jfP#Z5C7FiO`h_K?2jo^h3IMY=%h4TPc=)6v2$x$js0J$Fcod&nC'
    '>;;!;at07mYp{$=tt`Va5<Lb8rLl2>Z^>fwb?Y4JKq!30A|1-Mk|k|^X*6u>+nVI?(lKSqkwC4G7>gmS5T3$54-7_4=bnobO(Qt0'
    'Ff3ChmJ=9)T14opsoH!R0Bk8&WT?QROAKa2cKSSuq0sA-<pw4m^G5&Pfo_G;A8QG>%x-`lA(EXzq#6~%fJviM`1Iuz_v8ja2KKif'
    'rl-@m<{dOx9hOuST8MI_CJ?%zS@l82G_KqFkvgh-VSZU+JPJag+G|y(97H`OeSYWdaB6^ARDd@(6F=kDp!C;~S7-*Y<QUjVIo1j7'
    'Y@<N)%{<k-V~7hg`?yiBP}M_1vQgIDh7KX!^B@8AG=oN=b`c{Y+==83I_uU53nErHW?Mo`FnAD-z>AaO^)6;Oi&h9{6!auF06XOg'
    '%Jo5ffGfY_R>CInQwKtHo9aG_Mf{rfu}zzLfz9VQdpQ7O-lfHVb!4{JnfOMJP|9WyZTQMxDD{RNlQ~K8wya93fmA%=t_-xD!jQuP'
    'T~c`)BFN!%Bk58^Su5VIGe2A}4L6OEqz-m>M^wp3KE2Ta054S2nXam-`)2l=qey2KJw_f;{0yZ%K;2wU_6#T28zL``i1iN<^!4z9'
    '1w8I+>`V+Q4b>a6-ps`H37!r~GXF^bvfeU|%H!nt)k8#1^(M(wM1mrOnvDkgNyWr6Rk7({OO2)14cJ!62On>Ekx33EaMG<|7&M%N'
    'oA!qV3za!Z$vC!?p0|!7Z#K)ed2!B-LPR*)xNc$aF`mtgrKs}F_`y!~>Ptt)<p-VE>%=Sem9MmvNO-Qdj!|>!fF|2;Hs0Yc@BgJI'
    'Cu|J_5<107^zT`J)?7K`Ikcj`R=}@PS_CzvUhX9j565mn9y6T(rL|wmLI_Ao&lOwCxlJh{a)T#5dGN2VnQ?z1pQ<GJ?NQoUA?T-G'
    'FE>V#EL#3cidT9Uq5EJCgT$@PPdDcQ7CwLkVf34F+#p-_qDY0@kLe)T_XcS#w9(L6Uxb7x;Cfj-(g<w|90GoK03Zvg?vq$=D-R>&'
    ')*SR<5;x?~%4JvJu-%3;v7p?H!o~Vp{>21da&4EMRmgsnK8;b2PT3N&7wE9Z0;6JgmMe0Mwt5bayT%D4_?5dT?wkVB7jcfRE<B-T'
    'oTHqWIPY(FNB-DN8DgDnl~7zR{qIP5Pj~VaMA_eEh*2Pc^?+kFR0tky4FkXqgH0c+a`Jq#sYT+GgqNFA;>_Th7@E~?-R_c0w2tkT'
    'UTDCgOHo1N*hwudV7oWgID(%Zl9p0FW=|d>6ou-*V_?%b4;|hBoE{M>Edp=6EAQUZlb2<xN)jNu-IJ>%&L`jxrS?RNwk}#W)56HO'
    '2y{y@oY*v#pE;o@6a&C%0^4oBzs(F}BA6K>HgNLM%-~7^J#3-Ay&!xZM&m0Cm3xxL+;S)=%S5Ly;xJyWU@}St`rGUH*Y8HKCqTB`'
    'oejHZu#2}?Mxa^`Y)L=t`cQ)DO6IezrH>huq|OWCl|qGUs(y_dmoh22tSW;fo4eX4$fKQw%uX*DxqfdW=T@H6s*qn%1zuNno!JUO'
    'cdW{11GL1)$)aWW_xeFxj3+R?IjP4rD;2G}=sFLX>U(4yD4Y2i4BD&S!4=?5b=Sg3Y|nwdQL!1g!XY~b>Jr|S2GzO7Bh4z+4>qVU'
    'q4R7(33dSbxmRqDuZ-QZTz1Ss*;<?0(QSG%Kd`b73W#wFfS-fxIE?~TdsgOO|8T1zXrAC*TxEDo2OGnAe%Xb_dE%-X69I}QSZ^P7'
    '+tHFs^ne0_<(sKuTZt>ISA}8g8wVlFi7`z<31N+G^n~WX@}PydH5$gjge2e-J(GB(JB3UcBi%DQl$Jt5gkwjg6-7x9)R<&MIDT)+'
    'VOS=bF^{T-Qxn={%}q(W(_}ioaR)?{oxe|_3o0y;Sp|B~^|r^f2;C{i09g4A@3sZnp{%lRP(Sm`kNn7|g@2L`%5zokNHq&<%wmZ}'
    'LVc2Th_9xzAt6vMJbvD-Z^-P{TGdTwOoytF&0_{EIcEYTl)*wI%1j^8Ejo`GDjCYW|L}9CvuOrfHF!c8;cSat4`>-5OS2B0RH+?0'
    'Y7V^TO}1*V7qD;^Soc}>;ClRapWZH=kqrH}-7L+wB5qOJ69HM#X+LKVt_FPw*4dfnmEz}a^U~R~kNvtqSs`{LNhbT2SybzP5<Yug'
    '-L>rYl9XfhDI>i6o(8#a*l^b($EIphI+vkDI*V>6dPE83S;c|4ZD9(72)lk$q3ClpZMkRcjTe;gutKM-8FgC~_w6hiAp-S}1OD0w'
    '^z$)OGS0_h-M5>&e&YwXn9p>I!m0?bx2RX!ej43q2%`a9&4tCOxT*-PB;|6nFs{3<MnZw_V57}Q84F6(;@4@*xzCYx%%(}B$LrMZ'
    '@COd^nHa~~3iP&u#U^c4IuHfqY!RJWCtn7m1+v#O-p{btQv?7yTqY@9+CG!c3is+YXEoion~XBf8UQ=d=gHoiPk4dU1v5?J>usa>'
    ')YG$lDnx~#TY-?LPcQrh1<9jBSK0B#BWZDD2!DWvxhd~{qR@ID;8AO&?s9tDZMzC%<Zv6JJh0RCIMBk0)gAYsb(2#z-GSt7^&!Gg'
    'ijfX6C{PBqwq7m$u|p{u^oQ5ofW<4P3@ftnVnqtjit{Lzm?(21)9Rg&T&T8%LbnGT)*jRv2c277S~?@yNokCR_T9s{ZtQciMl?cK'
    'EgiP}w%&Z$fQmpXYgRIDE5oxJXT>n@PuMvPp3L0D!`x^?mo~0jFjAxm$f2EONG&}qPR3$rM2t-ehC$0HCFKKTrtk++2|PxcJ4o0P'
    'D*vxOFshH5Q*ei}W6gMnhNPQCg|Z@1=y3MTnsU@x7{+l{iFxv}A6ZTi*;~+0mvcdXQ|Gps`Q>02zN;4q)xR<Yqjb-v2d&b6yB3nz'
    '>_~w3JQc9o+X1@Dg={v|tXA?^GTaeA`-Ww`d5Wuj9@Tx5a2IgPYL<zC|3Y@REq;eCnKePo<QiS*w~>?TJdSws$8wN*1(cs$1d{!U'
    '26~j}f--59_B2ea*P%rR#_vBrd}?f_>T9Q_WU+VV1q?G4g|bdkBc76tXhQP<x&$!*Ts$_{sXDMFYB*O7!J=}#ATyp-L9{!q#Zv5p'
    'u)}+@*b3d5-{o2$6_`e@mY}Org*!EeYMRzM5jAWj+4-<73bt9GPUuFIW8=|VZp))$azI>cw_KjuP?`pNS-etLSJuI0MVjr^>z2_R'
    'tn}|G&{x+jS^~Koq^>@2qmi3h{5dB#-%rmz!T{_+xJbA2%l#2ZY&E)lvhCKwx@_Y|k#=;mAf-J#nsXQ@z{tyBd(3V{j^G!GIS?qV'
    '7M$MD8H#gWjr^{9fNAN(3df9=(`Al-Czix-)zy#!$vyHR@a-v6V-#1~a~9dyV_t4)B_}#&BG_1fB~3F&E~0Dd#v7EP#Sk-c9$<Qv'
    'W4;`#xt7=%3>Oyp#r{#g);in@-yRR;UVKB7yPfeu?TeX@O88vHyl@B=S9P-A9N^5HfW%%yRb{kzj`?H`nu85fi^?f7Z&zYmH`21m'
    'nMP6sTsF+f1-RhHZupoVw>{wgWQGNWoNsfXxnrU37N3bA#sK=nDA^!Fu~Zz2Z_0C^h!HvpAq@vCs#nuNYDJQSlprBARq+8LMCijE'
    '!Cs75RHlvIf8cd0l)8+bC!QW|6no3-8Q}6J`yq#LDvY2VrCrR9mq*<=7i6qOmvW+(<W*Jl)vH98;P6-O4S-S|2X)EbsANL)xk}D^'
    'rO=_McseQT-T;bIB{Es2C{j<+sCtFbW)7XFbPz$QVS%wJh#pJX-Nb)_BAXSBdN8<}@V2QQm4(>g;j;`Bzm3I%9IW33yHaqwk&!F_'
    'Vg?kO-=FdG19zxDD5wAYeXmavdzrnYf$15tya&gY7#w_rejLQ93UOxJazSKeThr%hJHW68YorDJ+wfKvf~!|sBNe+GcklvTos>XD'
    '<{CDQ%xpXpY8bG}yEtfiTdz@o?s=vP=vDm$<pfRn>NQ#O=UV8rQ}=!ve0mZoDuCGCgZ(wlfl@W;yY72(aP(L$Qi62<@#)>^1RWly'
    'x4aC)+e{o2riubPjN(I-ZWP7R4f}Gk2R5|Gf2xq3c+G`+{lL{^-1u@Y6J~!R`M>V?Bg;$medzw#TD=)Z?czfzrmxX3Y07DmA<Ril'
    'B5x%7-2}l;5l1)Gi-wfLspXHN?XQ8grF+6MU(1oGd)$nI@x!o^n8WAPVTW2o)&xsUL0CR+NWl<hv^(mtOoi?7=ybN=GoS3LNO8q6'
    'v&fi2hY$nGCMh4i(}=jqjw|s)1Sx7`6SbO#2GO?z9qg5c3e_7Z?B=hm%3y+l?iM)I9%+;*4eNz$&7nZ<T|i~2fP>qo17k15oy&eX'
    'G-z%v<)WcJ!!=n-owir3q-{~66HgS7CPnD4`y9Z6q*(5s0qu(RPKM{FAYw7oAM524P+yagvxh0+gAvf*Z4xXCMKL;i7bj6tb|d&F'
    'Lp2}T-PgB*dv3te+*hV8k!G-j>plmNX#|<a3%wnpuN^t7vo;#LS$Yhg3KRnGB~_oZrzh+<lU}ZJ>dF#EboNfj(qJ^$%?F(U&dZzf'
    'lA*Dxkm0~IumBpzb}t0I()QDV%s2eaco3~qABZ;bbR1c8%}pJW?G4c`x$aT;6^jy~E}^p>nnQ(O<9QrH4_!4uIevT~QCk&<76!?s'
    '3)5>NOv_0Y10MvC$&)wjJbYc(z13k0H%*#G7xwTBmx-Z>w0Eaqy_|=$UOZP71nG+E9_8BJSbt~9R?bg3p0OES8-o^9mvK_rltzZT'
    'uKdbf4FkU{5jeQKPIV=z`(~)bCk4*Yepa!=Yl?wTLYP`>eA?B~QSUdldmmf7g0qbvhEmc84trQBKNBwCW9^$%U$tixrIZRRpy+Z#'
    'oq9;R#OVkSDL`k+B&ip7JTCK2oSKf5EMFXbN+F4^7q~kI=qTaszA}NQbE5-R0YF;(gnt}$)Yh`kt>CHL`M|}WMNtJLf;x9&686R0'
    'd0<QIsf(0;fN?Im*2AufOP1Q*_8A^;y6$ak3kmFTwuG{DtGvoZp)C1L*O|1CxpU(yqk9_-ok1xDbqA<d7G!8Bd610#BKA`k$r)65'
    'lt%T|?tw{$K0{jQ#nWdu23XKkujyon<6Z^)L8RVSkMB%Gt4!W7q)?Z<lX}|Lg@F{61k^Rt9pui8%#yYA0tS8-^ej5j5!=(E@fi!L'
    '8lg(ZLbR~S+i=-ZBVTKRNd=b8<CNVEOn)|~sku0mqL6sCO?wVtAnzWiJw}`8@}dXWc=^<X6L`5yP|w3XqZ2^LYXoyL(tlF=d%i&W'
    '-~@!lR3B%65(ER{72KpQ^r~h3zJcf2KfoyDATxSE`)o^+oppbfN9p8L9tOZ&59Uv*0~iEHgcibW*@7b3ofBKYN^F}Ho|S-^VQiRP'
    'uK@=GTgjNsJtuOE$_-1UKxLH09s9AMaZ<Ih*l<k|?bB?^$L(-5kN`uJy9$GV%3J~~I($i>2KhQ=076<Xzm>V^({$M~wzBLG;d~pH'
    'z6HfVKYe`n({@-$mVUwo`(HdV9=#8nm$C<EsvcdaB?FMpe?aKTX^X+20raGk|IV<ILi#?!@2zMj+LW_&;QF|)A0v8a1ChVg8|ghJ'
    'GQXOw>_)wS$tDq8X_L2>OsDJepY6eZHwf%^I3q|J&(97N7RObl9uK{LlDRoxW?7<rMmj$9X*1`ybF`|+m%C9+78?v$6*M=ES!$St'
    '0?=O$+H8WZwAOCbuWy*_y><Gd5?<DB5|7=^>ziyw2(&X%cZuBo!b&FBn|8wZ2((?G$O>mXL^`p*QE%49?QMwwO6ohm|NQXDYp&`@'
    '@*TFRo<hpGEy3Wa%(pX8)x`eT%Ttcy_ppiOsOuVXKR3jWXnfsk#LY-_89GYOcX~(%lX@3jUHX6f7BO9Z`!=(Pk9ELazpj@*w(IJd'
    '_}cU|sh!oxlVBRi<+<PC!}}D~@~?lm)A&E0*qH(lxeMuX<f;j+>&UBO<fglZ_jK#%_Z<)@H%R)sW^y0HX(aiaS1(}Eh9>2)aXPq&'
    'Si=eQ{ESkt@4B~eveUnMvs01>6O1d6CdUTf-rqFpG}dcb!pO!SzkT@l{`a3ABAsnA1lfSt`<uQIL495*bJi%Qs=?aJ&)tDy*o^pv'
    'j4%;$0c@BZp{NQWG_t6TBpG;$Y1?c%M+fSt5gO{to%)kjvo!YmImGq-I(e`sPPp<(Z)A6qn={aLwXBpv_dzrVsf(v0?Xqjbsh*!4'
    'p-@m1Ruzm7bi;ENK>Lyh`+4quO?x2=&mlPyN0cX?U;MDV6cS4*HFP!*1Viqos8h5(n%u{FI54R7RvH;Upw&xm6V{Y9Ni4-Nb%7x$'
    'h1Spk#SEL=*@e<juse>pI6oJAMnF(XiQBXhn~dDh>P>8gy6#|AI>GUtk^5Ep!D!-YQ%oHJi3!q^^tz*1TR5N}#&Duh0)<K4t#!v}'
    '4p3&uR$88X4ap0AZ7-@IkV=-o6+v8!=AdxMeSpqUs%<u1iUj0avTcJSfjz>yLHqbp6YMn>y`#waO?hp?RsgvE*#6SkccBWsezbT-'
    '*Mwl$l=btv5j2mdtJDQb>F2AK8*D2H1u%NmspqR*lZ}h}ll1V6qQd@~ef##V{FDHf&q3*%7zCg^{$qC!zp`n{f0jM|{MJtkc(5<<'
    '`aG5PLe(C+sz$(t6=2-XjCe_1B|>y&h}4L%(0)$3FI@r^=C=ZBY!13@5r}p0q<03{_Z%up$h^L4n%NCw#Lgp5G*;u$)kIvk?_965'
    '6lAK+W+kVYRK#}kI|ZTx6-7vh*{d{$Z&weJZEaa8k?NNEn!$yqg{a8Zo^s<PV<F*?xQ3InVW6zMu^9>p+xF68UoYB+;&Fj!>J<$z'
    'TSHweSOfGyWAh$G%4vW+b#SlvRA|_O6h??G=%5!$u{t0IrXn|OVV0h1gp7u+1HN6EK?&k+kiozl(8aE+<J_RlNnVB4O|gO~c9ku8'
    '9)#2lFbckr3|n7$4kM30AiPdYN`UlcRc})meuBN#r>Qn>iBx{u1;??f#j7pm92)VcJ}27XB-@}B9V!m5pF=c%efag=*9YR3P86zd'
    '?^EEg?Z=1T^q|#p=cGfe1tGGx8H35;Wf95-;?DNaRXOI#IyrmtT$N1@mt=KGRzDO0&~}$hb;(qhOf^%c%Ays}nJCPZ)60@&S7SZB'
    'kWXoK@}ifNc1dYv6r$8}st^a7IY*@!`j<?0$z+#I_Cvru;?d8C^IZM%4mPw8Gg$5;b7F7?$&}1h3il;<9=sfPt21izOqg+%>?-*Z'
    '(z(v2y4(-Fm`n%Oe9(efX0q{bfBy8p53iZ{TRbTxapcyonKy9$XOcICxANicF#6!<Av1H!{QU7M-u?FB*LVAi{9(6H+vL<Qefed('
    '{e*#Sa-E4!AAb7#w@-&pSnEm<o!XqeS;kjy|IhsSr9@&5jyL(^w+|oR|Ni|ifBhz~nLl`cPox>c@9)%2c8bU&tua0za}(dQ_twX6'
    'Brc=bLyX7pijL*JCuu2D!v3){efdM+_sr>WWM4YEiaj6X`-=GO>#=85{+CC-+rCn*?7Ll&{lVNOIPm5Sj;{*BWXjQvwcR11Gl|l{'
    '7sNS(GEhw_AO7jt+!VV)YIkmuOY*ldDyCnQ_n$o7(`W0Pz={l+j(>zB?Ur(dbXKkZFv_C}`z4IwlFzV}v2@iLDfg{p8R^=ek>tAv'
    '>Zf@AW>=KB(9J@gxZ=`(zVDElX<jlHT;=8_%i=s$T?;ck<y1VQX$9^1U2@15f4<-UShBCsA%_ItNsk<|phLR89FlvvzE?Cqz(+aT'
    'jAxThCPhgXLnYPSHx-P`a9-j6X`5L@@O$kwHw&LC)#Z=fZj3%6d8m_Sd*Me6iatH(>gT|Z<d966$9UcXTVFqdT22d)d*!-?tR50^'
    '@Q;E!$@%%fLWbkCOy5voHZH7C7vjy3GkirL>fTs#VRt{OB<12?U;qr1x3dLBN}u@!hD7ifFj@B^Q(ewds0iQMJ9s0VsFO8YetXGX'
    'M}@)P<x^cg)uoqT)qnr%A8s^s%5-DK&Tm{?5Tu&K4)&E~i%m6?4LE#3^N}4~0}X7$YgM%Jll(oy!z=b7VLDMN$F@%<Eb&S4<;yZa'
    'd(*t!*m*5+;4dg>O2Qg5K+hSrBMka@yR(77+nD>nsluFs+Ravh8~u4EZQj~4zRFTpl(biYau(x2R#VVChwTV;qRI!6x?~@2mED9e'
    'OcBYg7#d1Wk2q*WK9bk*9CUkaNz%3lN-tOB2<6kGsyO=_kS0S4*9I91s~j&~hEP36RoBf~Bi1RDQopUmWkzu+gCiy0gdfns?I|eL'
    '{C$@monP1+OS0|i?G=4}bYY@H4_D4^dnz}PK@?nRSr5InHVTt`1Do>7X#X~{Nh@Xbi`v{|S}B~$j9`9JZQ-!eB^0m2lHVoWGo@^7'
    '@G@;)>OS^jO|HXfV?jIa1x&}-NG;j(dSC)9HHD;=+~6(21a{v@@_L5Xh##Q_2bb51!R7RT1Qv5yy(FB-A>~-BM1rKIYg+%xeX}Cv'
    'usHaJv_@cxmsXY$PrCk6CJrXQ$_AqmbbxJn*)z?;rH){p8T#!iX6QBW=k<)ery0XqB;p)ri{>v^U5dq&PE2ei5C1onqNGxR-Dj~W'
    'vC&nszNC<i?z~U*;d5jr-vkRKU-cWVns@0~hDpz=BqP(80PV;Rrc%OmeTG@=NPyQPwJP%oF>kRn%L}14Jd>dO5ojw}9$c?pz`hhu'
    'rXy<EiruQ@6rU<KGy4bXGdhckvQTgUeV-aSpIvMle|T#!HB&}1MwU=WKsk-?8d$>D`Tq06r`EHg5CZCUO=Q#(MTW^83TFH;!YXi1'
    'JGxw2J84dFV#HCU_rCN^651sD55Cd(rI8qn_6oPT16Sy%OT}*Hc(+ob`fM_=vHK;LWmh)1(5kVrqbW=mELW-NP&js;6Yf(+d`axt'
    'bACI85C7y((*tp0uM<`N$J_8<zJ7kU`*HjE^FOeXB#B<qy}32f7;@2z5@i%3t3BLb^RfkxmXQbKlM0JiJ58!hvKC?MAZADc@i~#h'
    'n@*Zs;beZJesSz{dY_Cbg;E=XslNLhN~{>uK8ufT*}g;T<2`!qqWYPsQKvyqT199{EKX-y-Cs-p+=+E{O1Sf>>Qci9Lpy)Kpx&lf'
    'yU1#Ec?j%nDYQ&m{)N|uS*%Yid7KWVYwYorJiAu~1CM7Lo5sR9T-GVad(B*G#br4;K|vP}`6u=9o;xQW5m0$}c)IP~)xOVQ$(xys'
    '<j4#Jx@G^JUcEkl8=TYm0<hpF^kd)8YJr%Kimz?*4<MK&rPfg}hh<_`Hvx>@G^J8iU4Ks%KWULKR1>fsy&rdVA~Rdj@czedA3nbS'
    '{rijf`VAz}k*_~C>Rk97&$Il_e3GvHx**45kl<KuGl>wc<$jK-&zh7}lNweJ{n)}~c<S<=2%gk8Mo)VkJd3jOfXaO{CbC?Dp-Tk`'
    '+O`UIeaK}$I2hZzW8La6|FEbakwf7tb!SCOefcNc3)3S(sw$jyhi`UINS(LKuv>#VC7Y)3T^Lu;+yN|6^octg3)iw*Kd$66xACe*'
    '5$=wYQI(kQqNI6^CC#fQ8}49|lsmww3+gCvpc40*TJY@qq^U19+qygp{cX=v4SM!rO`;lBxtksdJK4tcWM+rluQf9p+aI~}j}}5a'
    'n(L)7=%zjF6WT5p2(<+q?J&ORk7_1A>nVWGmtVHqPhRy@F+7<6PxS$&zqys_6B(es(#fVzIjJo?mlQHGx|);;egmNAp?4g-N~oS9'
    '_<E`Sy6znhf|;tou7kIUe{URt`pS4RZ3c!uR>J(V*lcPjZ}N*%9BxU^?y)7SY(#33OiBmG9WB>Q&VM=Zb#R5|olAmwr)GPSc57E;'
    's*(p>^7WMiTx6rpA28rHEUdI^BsK8Md}V}BY2<p9<C1|sTyRH_VvX2=|199c$ydK2#SgCQ5`WRTGD3$+Z8a*SaHuD1cV$i0k+#=6'
    'Pd5Nb#0q<KiPvZ}))_%}so$0Ud)7TyS~vFJtz%z|Fz0?%fVnRc>2C{vBv)xYyFQO+#N98Z!ks%b=#>w!BFcUJf+R(0a?9$aC0%x>'
    'jbROByY>L4+-I0OrR!>m^MLJ}T-31TSCt7S$MlSEAzkF_;tper%X*ePxn?8@A$2gaU9Cs`LMFkY?76*lPj~?J_3MX^e}DA9uQnxk'
    ')x>|}Xv2`bgHeL)VLsjabdNqBq8xlzPAZb>2ER%pTdrQe7LW-4`iGlhxTOVPU4ZFyxs!9S%pxdd-d`lMW+#Hjcq67r*e%7sb0~98'
    'o<S6%Q7Mw1qg?LW%BMe`buAP8K!&0fMBtzw$)tKz7eOUx3n?8VmV30Xeg?b_;_&PdfWGQki_~Cv&_tECphbCgD>D~2K>X0^r&EBM'
    'veXMGi~JH?LwA-WWBXJVf;UX6$k(G|NVCvcmVT<Dh`mnKE23>Q_!O~I+dJB}fW;8md@VfsG%oqZck)IoJ2GtO!-AJl%AzFwun@y8'
    'kOxMh`YRHKNorRok*d44+k(zrS%JFD9pT4szRxmcb*oY_E)mw>cz1d91U>m;_kpT&8*kiT_IloRZztOHM6f(3LpK7Ex{xQD2Fs0('
    '7|w2J0W@VsvhzX@S$0*?Je#6^#D3?dw0BF<W6*x`pz38OLxa==BKDd{se1A+8U_$u1iDFSdGZAXkAiufyH$Qoo$x&RZQX<!r!z&F'
    'jD8I<;zABBB8R5pMoQsp>>)!V*Shb|=okkD!{$*$D1AYK)ybXBNLDZ#_d2r{wacUPa~3g%9r|wQkKy=Txul=Lp)vTC(R`1)<nAZ@'
    '0}k@NR=oedg(7TLH6pl9`fm9Ky>Jca9~L{?L$sW=-_<v4Xw;Q(Uz3s*jGK(EW1}`#ufHlanx3pQM5#NDtpuI+_F1Q~?*jYtk+Sb7'
    'EHXFvZ@DdJ%QOSaB3h-{ci|K;ZOug+i3#(Rb}Z17%rbLm8!304j@4n`nxc`9&}k@(mkC{<R4D|IuEiJ%1mez867>0!h!v|5?9HA;'
    'Jge2XU2B7;9*7?f)7#1O!eGqYmX~<3LTO!i{EL0U<*MUX)wt^kv7db$w3UBS1aNO04AXp?3%4RK)pIp<?5*H3k|2U-wl(67I$wrD'
    '3#rW3%3ww-hErooViyJpPfBu#bsuy*{9yE~h}I|LFGSm3IaHi4E>I`~{mRh+A~~w6YqYN<G8{-I^wtbc6N{J)R%KG<d<^}H;RMBo'
    'SXA+fA$I<{{rK?PLcg<A+9QnKp1ap^#hv}1zY}?gGamsB^|(m@aqG~}1Yb8KXp+N9N}_%<q8*f!g<(D!Tguf&ZN0dNP7|RdOj#Sw'
    'tI&_>MQ%7*C6>)xyRFnuxMKMi)dnb8C3kCFB)ow=woLL1kp)J<9d8){KZr6}n0?l=lzJ+-qw}DFHOa1+AHRM0`2P1#->d#_AemTr'
    '+~$<XWDJ*$A<4(0^PgY)r-z46plL<n876I{5nNknrITtV1@c0>rjIh8qWxU8*G2xnL@6KS1f|u0ec@(hh#d<Az+I<KVcT=qnf~zc'
    '?~nfXzZxqe?YrQiCl;6sqdiB@Y-Gi*3u6H%buW6tjX8OkKZ*jF^pKv!1XqQ6cczV!-TmfM`Jrd}&BP@NIV71qbSUM6+Mzabeub|m'
    '1W9r*=^57~S!VJUsiC`f6>>UB#mT^-@!}J-Y=NY%@<qnF_?;C|P$c0y%3@wH_qgxrOO=8b#O3wR<A3HR%Pt6j+vMT!gzNRD$w+#q'
    'lWL<NW>!9C4Ka7ZWs~uDf9B`D7hmuHW|+F6;!1<|?_>XYN7^z9n;O8VC}dBCgb)iOFm_x+6>u9xyhiZ+{N~@vwy54t5N&?3)+w_F'
    'mvY2*Ckni<_0dSW&@zZd?o8(&s2vt6rf_$%>a$3J#O~}c7>sQ3!NLvmpntqjG?xLX*o3nIDRD4g^(hry>02Tw1FzAkp`;>lc>U$-'
    'hLy!53f8RImW2g_uKYxO;0@*{_6k&}dqxmsD^d|&8jh?&RD(r=%+3*UQ5a~=IXzBumr_X_HnL@@aO8xN3`8;~G<J0hmKIyH8ATZ}'
    'zz}I@aO_&3M0N3^zH>hFspCi8i}1rd^Ebuz5ZP?+;5toujxd~(l_$ogERfupVpZIC9lfmPScryDw)4nV5?OwX4_m`dq?$0n2fnlJ'
    'Q~<j&PheXs1baE`zm)cc<N?0WX0c`1C3QK-Qj2sdB#S$F`;Szs7HyMC4`g^ZC8Z6fYU$?k_Ifr!i&si4+zbs}-9aanr;Y71l)}m?'
    '0Fi|8hOO4<&M63$+=kVb6Kx;{H@JVPVc@NB4s;>$t;%$kBB`mI>{R-)&bvxtGj#sqS2u=sb-kMb3ZS)wgk*A?>yO0VQmmMw?b^_3'
    'xouI4&y+#^7}+UGsOpK{Kn}aY2<_}M33m?<k2Cts;%_b;{_WF+_U`tt`z=c3EL^Y#Uwyb|AH2o;a+DXkagzP(`oBnXmGyNNxlzaJ'
    '=}qYnzy9kss>0lxxE)(depg9tmR+{Ot=e#=iko?FCnP(KSk~fd5#-M4P#!kePUQbfNy_ja$TP_&yu>Yp-5e%M*K+G2lb>oCyK9bG'
    'G@s?HIRmUJH-^-O1qwuvgJ@V-qXHI{New8ShdlnRf`+PIo9+rCi0c7Kd{R}Ao>{xsj*mhtYH>pJ&}xoNzp9my!&i-dDwZTEXTMC5'
    'aD?hBq?gga#{!{_S~9N@sftb^$X7|m5b7@_5w=Ml+RXbuDqZYwFjb6&53=;za$h>x2ltnS<#s=ck#Xv)vL@2yWC6cJ*o*SmT9>UC'
    '^Xc|M5(l~ZR^wxJ3f=qW0<V7=ApDN*HM{b$e^Yy^nouIK9jI!XMZ;bS<@dsaz%DpCwL#&uDBj<A?9TN}{NgiG*}<k7VT}SnOCBm0'
    'GI#7JxGtQSm4gndciXl`c_{nOs1z=wUa{XL_A0}ZG8Dgp0{v$gqc#ME_s~^LD<;-64>T@U9i-1#Mx6UQ$u-W_Xb%{mAzr<HT^^Z+'
    '>c~*qvXaYmHZxLNU^M}Qv^5JqcDVwi6VJ7R_25cjxzfKUM$zE<EYyFfV*9)d(d1gb4V}GFus#k5@Ws{RT@9|kEXE}qhqEu95UI)@'
    'r+RwagjP3fv2Q56jPRk;nYTl)sh;RV%Cy(vTzwsC*rQZ9dFntD@3;ON?CxN91)fUOgHmVc6$|SE^f=PQ3y@UDe|d$1qa0)HnPbZJ'
    'V4XN@x!96Jq8*;p>wwrDrixk=NV8YoqE&{Zp|ND3=8#uO060pbjKfuKazc%U40XV$IZAc8xwux$N0`YWV_`kXV9f_nVhp;}DkBV?'
    'K;GL#^>B&+2Zj1c3!d{De?>g9Lk;!>_Q%o1mr81lc9qgfKP$y<Svig@K@3I|(LzI!1$~YEv8CefD?KzSd6ymF%?2f`V3C4sU!%SD'
    '6$dG5Z7KDy?~o5;OFH*s(2(!XRbSJx-&Xs!L@b5wiZdArO4$1?g;&sBxpJR+y(c07g-Ns7QMVAE{bfa{U6(h3(3;Es!N{x7MW~>L'
    '3~XKOiOo^P)bFG@XvGV+9gri64a6d}%E^g{^w-mHXsDp4@&^3_w)|*Iv_a2^eltC}uDP(rnW8RXKLl+-;7}ZKinr9&67am*p}2)^'
    'cXcDR=+?0*KfbEn&d_Db`c-xGbLk@w<!~}{5d2KGEHjWX)OCnoG7!d7r<Xlj!S^w96CM*#(+*aw2OZ-0lyj8ki{Y$G(&W(cK}XX~'
    'i%+yHONBs|0k3V4H^-JEG?qngDemEUDLtfE`jkOt)nG>}DLQice7b(Jjxgt7@1RAx!ow!F#tjT7xSAoastd-sZHu-)|NP`1ZZ5p4'
    '`Rs~LP+)G0M-vW<fgCnO$DHbD_qCKdbyMDrXFv9WB~r}axSj5I*0ESwXl^ELvv0_ekYmRt*y&<1EsDfG__~Q~7{rdnC~hujT21x{'
    'Vo#aH0{CL#U>emc9(4BP!oikOY|rXU2sg^Yk>{UP8q`m%xkL$jK?g=OPL8ZYbi*v4@52!+#3pn^?CQJ4ry;qjd3}*YF6?Y2)e_8;'
    '%aiCh(qPwDRd0opJDHCI>vApP-Ai)c*1VUoO$n1NrG7gL-m-ysR^JB_@_wDVQKzKP>i4k)`Q!bEpUaypUF#&R_jgOYT57W^00@WU'
    'cfcuY&XS4^(hB*!jI1Oq-6Y<%9n!{juONdghJ-JawZ(-?bo51`Q=QmV?>|3$BDp1JMTo9$T4cAYTYq}Xg|LGLvTIr(S_buvP{a-p'
    '*ABGFZ8m9?vcM<V^=2uGEZUo7iKSq}DbIyy5`k47PzA91jdKbc<Wy|2i8l%<6^{bRItR9Oq*ISC-1g5BfBW+F^Sj-T+s~i>@#tUg'
    'MFB~BtF!Y$S#714wZe&dz6g~b-}0}RZb??v=%}$9%A6DQBaSAsztWi(`_qBa*u#{TR)DB?tdle=&Xj^A#qm5E?m}@Kx@vi0Ho|_b'
    '*|H3i5Irf5B9@&e*9k!tuUEjhtOtfLW-cmcLzAE6qS_LAbd-uB71W<VJKXNiP(f`_A|o4)v6298uzgE6c<|%2ta*bn1!ttwfrCj)'
    ')hBGou!VE~Jd_)RO#;d{iP@8^5EQr|nY3%OkfE$055;8dBLF9CZ9Eg{On{tUYXum(4zAGIz5>9Jiyv0G-s0aq%ic@#=mnheL~AH9'
    'RhkPltJ4lJ89neqGg0gd44^NOe-^9$pu0~v1lUTOEI}L&UscGG@T}ve#VkJtqq>nz?9?Lpd>@Y#9a3V|h1J)3@TY2?DXU?_YLEEM'
    '_xhjLAEzgJySMl7=`$KUK7$L%T(BwhYOh8#nIGpJxao*~X7pT-R-aPKkcO^jr}K=b0U6eXI?olpuRc@NtCwh*P+~dm!Gq1FDILk6'
    'PNQy?RH67+!yt)hb&d$r&slkT4hSsQm*#d=Y4%8)^oPIl`t|F?51j=5rhe@NP3GyZ)s)y;3MO4joqBPbQUE~p1YkN6_GNvF4m4^C'
    'cu0TI<k}vE-GHZLrD^eH9lF-xV}>DKqK1OB$=0BAu?)V3dUk1z*TH4&^m0q3k4A2j*w`-zt8AB6z-8Sq>ju3lz{q@Cdq?G0UG|$s'
    '>*fq@tymfQqP8$}mCu|yLy9)2Eg-D%Wnev0h;Z?n2eRS5u*w~m2=570c&(Rx_}Omj-K-4MKFYaQYAs!nGLq5_PQzK9IcmY^f}M`f'
    'pz`4h6_oi-j)`bKb3KQ3LY}gnWf^<3>}bSp+lU8B{xJNeys~kKQ0SmAu!EwTDbh*Fg~XZi1R(`SlU3zGh3;2t8w~r#=Vz6DO-38g'
    'J$-UOLRXUc1wV8p(m)>833CU8OQVVI+F*#dt0$C)0Ul>rAa~?OTZ^EV8<teLt7i?3(c^!EQX1V|*=o+Xy{3B*h86(ZqDE6DS#25h'
    'JIjhK6TX%wIHOytuH(@vcd(owwB=*jOtf+jS@__JjGG+pfl5EpM*Ab#V_8weDQ8a=y?38RomO+Ik#ekV28BifniW~0eX@7C0Q{{E'
    'jMhYL2gIpL0KusQBUHVQbByn*XZq!!C6gRMWxt!#cqy0s3-10PGYHLkUB&!^4_Vcaj_I2IYitA8+$cfDa#<{Z{2o`rk=~~MKxd{f'
    'l0?Vd6k@umC+@^O`~GS^KOn#K_2JidUmwaCY~f$~b^Gz*H{yr(87|rT*{8cDf9II*fsB3F%H!LyJEDK{{pW{IPC|O@@AFxUCAywj'
    '0JX-`7Xs`|SItF$McY}_O?eEOP|B@9OXF0A+caDgmA>RTHBv)Yzy1hgnVYt!cBC{k>+#INW*|g=c8v8c0o7E-UdU-A8yRHt)-iEY'
    '3Vv8IWjGO82i<a*Tv+_;a+F;o=)JesH;F0QHPyrB1=+=gG%7fOLaCH00XT@v<D9u@EH5swQEmXt1w>h{LLYAn_2*JSPgV<=w(s=s'
    '>3V0I7Eqy70~kFN^ZF66KtY&=M)Q{Bo=^^JothRa*)d}qnW^b#wd>cbR_A<8+e}v{(r=U1Dl~oS2EJx3)0?UIgjKl6^Am@dts&R3'
    '3$ML~T@J!&%1-{J!MAH1<6}{?Mp)ayO)ZpO(6_(R-c|VkQ+BOzRUX3XRXc2|Ey3VARqG62)F#rO$P}&d)_qP={g|yb3^O)1tR)BN'
    'olt#-oOw)S`zB~1ZawY|leG(3^%+y!TW|V_?%XKz#Nd5fQ{15>W3=Dhr73Ojde2!}HjpQ{F*hnn-AeR}qDL1JMem^T`8t*P4;VO_'
    '-`6YU>q^g{_b;f*fQA@aBal~(77~%}`-p%-j(;4lA*V2&ZtKQNUbRPNR`gEqh_rflp(bChI)9aqnta}&bS8eX!8Mq=^$zyEH;I&I'
    'P8MNA=?(W&*Zx^p2Nn@VaNV{rbxnV4Qa_ky8F4`DDT9<`bUPfTNx@+!g-r>iXUS>xhQ>M)i%@I0Pn7VA@H**0$LyV5Mbm``i?FbN'
    'bA?eXS;6pJMc+^|EBQbkLt%hfcp#`9Uy@}_8fda2+hH6bO-j>fCu`<%X<(^zvB|U8JL@Xb^|`an;E4wlkR6mbSH)Ci)RDmY7j0ka'
    'szfIM;ozYdOsEtdc@Z>#!`FOCEme=+r<s?%nosMh<(1VKifS$NBrCIZte`6iDtK+rA^6c^UIC6m8$E<bH*XK0Q$Bgl`W(}HDmwI`'
    'H&t}bpp@&m1gWqCk4Axo8<{Hmls!SC`7PUh($!_Kwgax~DKnSm^%M@XQs<4+GIgT6gIbZRb`{<UPEUr?bBZ3s{nTC4qcA$F+Lj}T'
    'VObdz%Qgk8Jr!G|1uFSrSmtB8wLyaAoV8xe()qrB^pNRmBE7lY*5kE%VhbFh$v$qX(dMXOx;N%GC9LC7lCO+snY&HJsbpkc`}p?Y'
    'piCLgzN%RUccu4bVHn2)Z$?V$`D4w6Y&vvRjkeSP)$9ae>5i&?YB{Os6OxD64!qR6hRbECk?u|P0XIA#qX+L&S-lb)3Ws$Xxz2h-'
    'mSd0`rF+s+lIW;U>-yY3Zno836M8zqGJq2&SYg}JCvC4_zWG^y_11(aFf<GM*C`gH;3o$g?Z~VvrDY0_D$8AT@kM7LJ_7k*twu^('
    '_lufPVR;w>d=$62?F3L|JfWZpJQe^-2ep1hIhZ4jnN~e~q-btyAO$?@iolWbO)6XERs_-_;wnfR@M=z$a$?aM$yt{~)4|oC%jeoA'
    'dgNnhr+P0aQ_A8#xL~2=>-t)T`fls!@=fLuLnGPSIO|%rXhXX)UNe@qLwHRQ*7+1nu;_sTML`?7b#dZFy}mP@JJ3l18j*$*y;PCN'
    'H<V>fC((l*eE>p_=(>U}*XHp>km9V0;wg50>nU0_Ew%obHb=^PiET&e+GY#<^j_C<W-V;Qs17II@=Zhf!$0*Vg#PTQ1lw376W`F~'
    'GR3h%CC0}fbZd>7nyp>jQnD}*U=Au;pF;;)k-;?-SyKkNALj50x3b1s#E9o&V&ip*Q04OMf=cto-_tJD_?*q86mM`F$?GYeu<1*O'
    '|Ez(b-1I7Sk38WLDK;&)QJGI5maY)<&GYgO7sB(2tBPcYN=-9G6yFM0%?pQlIx;^w2XtUv=O+<MxSlE44XnGIJEE3^!>%5VXpM$('
    '=nUCm$xR_z2{sDZrMbqul^i7PC<wjd3|JY5Q?@{4`JfPc(-$~pQDI*&5wmE?vcN@!3aGH0?fk}J_95zwo^9o=2bpg0s3CdB0?LjI'
    'QWw==GP&H{w!oW|RrU?)XC8`}pP^agwCcPJuCB|=xdy~o0}S5)zIFmnlzOB5-iC@#h%uVI(Cd>`b?ln%Au+=yAT4HOYdd5D^%F^W'
    '7JiLo5Zxf0>ArYA^ZvunosOv)6wlycVMIkB+uk*KEL!?@=+FvtDYl+{&%2V;z%bZUvMbjqgm+}r#%ViOo0rZ=hF08emOfmrTeqIW'
    '0a@Q^KPS1?^IMmPDOq47d%u>BFP%N}u|k)OyLv_V*pVce>|18hoGEg=c@m}4+_h}{vijWGQ%0P0@g&HFbBDVYIaX_RfMR>d$$+O^'
    '4*pmu&ngbYZ3|NvPuTUF3N2UErSR~;c5OBT<XK8MFjn{NEP~DwWVz6amY?Usf7e8SRkEGivPQ>P{WjicUIpMn`5d}xx$whQXO71X'
    'E^0k)>y3dN#LtANNjtym0dredURJ`vq6#Arw;N?KY70LH_ti&gb$Gm#j|tDP_*+`xF6wrd9%mic-43EmEP1+)A*-{biU`Aof6IW}'
    '@_>%vb`WgaXQ1gSxY|;sSs@M;=j%IYl|uX43B0;li>G>nPuA+4EcWUMUOiD%Y)J(Z8>9CY#@XxU9J!6POa1MsT6FK(;bj4L8mfpA'
    'S4~^E>nn)raY{ax^NADL+qMuPhpL?iBjkXcEZFx}iB)Hvc|aa=A0V-`9ao6+-An=ua$BsUC7RsgCTLMXp_q_!K@K(E0x4C|MnJ1J'
    'RFF(ik2Nqyhv8OeB}Ve^Eu$Z>B{p2Eg^!-M)x}yAj4JdkDPdcgWyAP1*RzBQ#)*4)+uO1=I|He)BsWr`Qq46q!-dEq=spIYUg+*m'
    'zP=v~-e|yGS66jtz^Pdv1^jCHfmJCs?ZXW2$PJeqX{v>qD~ijUi}6~ibGvfR4?Gr^Z&pJ8hbT?;spVi7lGMSEToZ`?n{s7{1(FZf'
    'wJSw;3bOPyg%*{HHL-DrbIuIdLgaig{=99X^9l*iNqMcOAnxZ`hZioYsMkW#LeUP2ontC61-+j(E(aK*H43jN7@T#PfmWA;ed4`$'
    '9el4mJkkC}eFCL1QU>&4A@i?1xP<;U<xpRPV<w41l(5$uh#i26rWV&QyA<3MP3Z>K-}1SWo2-K>{`+KD&u@OOrp6z~vQz==oJF3('
    'X*HDa(E+7Xr`6%0BOFd)D3A(*wtinw`W+)>VCrz-kiU17fqph-Ze!QM|882K|59fchb?+-MQL#XR`Z2RV!7s2<AJ)+K0Fu~#Gz}3'
    'D<sYBwVp^aa`Y$K$7R<DN<lXAK;-&ueQ91M>k(NCP+}XKfbu1dyDpeY>d0e|)`^{Xl*#~dlq@WsT;f0bEU(0PD0&nwo-<LOu(H5e'
    'r3FdL_T&C{eEJpPV-eTNt@z9y3nHNhGg5cv5X}Boh(Tu^y|FSZhpt(3pQsy8{M4JKPVv*&mYMqJ=xMRSYU=9Vf7sDgg(mW+sXa>j'
    'gVPk`?o_{t`U9n9EgjAt#R>U148?gWTB>!WEt+7$UzmhVqa|=qO*@5^C%Q%Zx#_+p-v;hvqz+CQt-35!b@XbF3U+F2=Q3bD+~Sdn'
    'qeGpbGaIhIN*7bT?UgI2+5S*Hr-Xs-aJ4?87Y28Rn12*$e<xB4DkXeUe~oftJ>!Mh`4#BN>vyHgsFHAg;JZYFtCe`SM*fIOx^5-i'
    'GS?q)7~#g=c=W2U`xpuGQd7%&dH^X6r-U<DvVmhiX7@L0&2LN&v5?F+5H?k%qTO{kQ1!OunW+UsD#|m2cP{kqZ1N<mprI6lj_w#`'
    'dB^}sq(|EmaA)$HU@fB$4t7*A3U#|>u{{$+pmbxEV`Zz-;gVfgm&ny>woIiaJpFlS0w#c2eDUlvVGoL<x3aT>WH5WLKyelB%_L0Q'
    '&^T4wXjV(+6xymtchgGpX4#q5;m?;%)JDTsx|gGixDZ>EMcTVn?}qyuy|*)Urk~DJhb0v&iC9o1eow!jA0|0-rnL?Ke8}2E2)|X5'
    '2z94eQU>Ev61^$vo!!URQ9&8l!UOACq;9R9a?*RJlH=?avOzc68RwkJ=5{NRQ1C%X>tsjaWfXZ4pJL$}EAnHpb8A*tCb|jjdN>~g'
    'YF?8CbT09#6`A3=>quZ400C&3IfF+<YIY{9m}&>JY!%~xEZ1dM(6b_}S9A4xPUl&JZT-$LSQh31w3DeIw<n|!=O9d`xV;9K;=caL'
    'xP)%9aMMYWZLVCwuKAHW|FSz%h$;5z7sghusg0u(Lx`w~c0z3gVgbMQCb6VXER@a4*U3_H@CYX0NxagF3Wa$YU~nysvXh5j-TAU@'
    '_!;1pBx4zkzB#?7H|3pzS%#!2RoQJZd`6hWLQc*a)3CisHfCBenAtZ_BobZ%FFH_teLA6`n?S88H83O8;q2N6BeJdb4nT_&6ug7B'
    '`l_5%;&YmET!))ZfX@2RbF0q$z-Y^s9yNwH&`o^^!<@`4&O#S3D9)B#mLq;$2d}kfQ728S1~858$bkk!nP!~EB@GTjx!WpPJi<`X'
    'G^ZKH$B{jmDUP!#w#>kHn4`vI&nd#TC9fnR#1?>%V>!Ygn~V!QP}x#7$Db(i(qfyCCd_<IMs{$SJ!}z&Y&2J$NWhf0jyzXh{5j^z'
    'XmW%pC6|U}@Qso*Lg8qc-8&0KsU<lrKxSCUp`79UM2kY&W0>VguuCQV5MBKI&gWz2(#XNX^syV4q5y;$Q35^tfJy}bNzQ*W2FrNz'
    'HIJ{IH`W$EStcqmZfLG9HI83X4eV%WqGv3Ry93(6pJHy*4ijSXDzE6NHW;i*AR`Ce{9CTZy!LnVb4x@l$Lu<?6{w7$N5^fW=Ie>-'
    ';0?j6eLL^eOYMA6<ME8L-`OXfYR;=yT{!S5-aky<mXgD3?P=G_AQuX^!W^a+jPTngFr{wp%}vPOuQ;@JD~DId{2c`lSimPJ4SiF='
    '7I*=nysOt8GH`w^m+>}Ky~FfzhJtGsKgd)FOqE6*%6lx~Wi5`o$N7YgJBu_po4V^Amvd8_o+2Hm*L~|0=P;|R_xB^_HwfK52LrJn'
    'B4VE$rImN@j80)lC9JNNun2qUxR89&f#IW^{;3PeO?lzPHv0{yL~@@S2$6CkD6&%m^^}9>W9ZR2)MSA4E=R(*a;%_B5we2@`|);Q'
    'Kla=QQ>9sfqpXsTUQF5WcuU*VMh`RK+a7!eVEb-k@Z_i?*z_nZ5yS+bUJ&2D6Wzwz1V(wc=Pa9E&DN!Hd=+$5OOqVX{0+J?D+0HC'
    '@?~n;Ru!3~I2=sNsZwFBY5oC&v2wrklHDK8({i3p)k%CRd#?ugZl#x$fjk{6c9)D+&Jx$JHpK_Z8k66t7Sh|AJDEvUFE_|FGz3Vb'
    'fPN20p-H*dtyszp2yx0&hG~8xR2em#aDDC$D^JyRXB_!qKxf}T_Y-oiH4WYFr#{~tU#3SU^Zr$u)ZmISm>mtvzD?4dcw+s}_-f%r'
    ')t4?Gthia{dBYP_)GOER8$I#IeS!S?2^jrZIguC*_NF75D0b_2Wxum4_h%Gz%l8EZK+@+8kp$lmKXMB#+6v8rOeB`@A#-*%C)b+S'
    '0JmW1(3c^(|H_=ch$W$WpkTX~A#Rq2HENW}Gla+%J54W!SyQ_zi_f<cXW@GPOSc|#=qAb1EZwf`XG$AV#Q_E7HjBf#*jzJMut<F='
    '^7gy*-NTUd`Bp<$2eSOP&)Yhj5N*Z!2L|dR%?Xki<FQeh!j2e3K2V+nsTY=JW#h>?9BpEt2I>_@4|#QUCx4dnk!DH(4MOZp=q%8o'
    'cq85P!Wn6QM^D%lJiTw(4!3Dqcd3&<c$SUrjC~FfxhYdG*TmJ8YH4~+Fo@9djWevfx{{S?Q+p%{%R?#utsd%2w$bGTF2Rt9wb#z!'
    '^X!0C_A->2;Q;k5$Z=|Do|ME<Gtz_Ua4h*{J))Ue@D(b}5&nvy^8+c|Ft9gS)af*37F+l4ztgA1G|iuieP^;?A#JvGwl7&wXQ?+p'
    '6s$=CyXpQfEZpkKM(SD_Z5z<7ezM_Z;R3r(VI5T|l4m)~jA>U6!LyjlJJXeP`|_xY>Do#*l&Qv6yNNr-jyqZz40RmXdE2b!1P1B*'
    'j`SMgUp)PxR-;FUdPIwDW?J@s^I%Qxyzrh1(}xY5YYR<!@2d4j>v?SXoyM&E@JY@yzAxP8p{t6{l&FDYQ_f+n<+^~hd?GDvGJM-('
    'qoLcx?;vfJQ~9>FGkb>TU1~WzS62%>d4k7N)Va}d?nG_k?<yEeH{Qi?J{OhE%?%wCog-y1_(N+K9d9%??;Z}?>w1S6vK0Y?iGpAH'
    '$8R4#zW@EFhlfwKy9gVvWq#nL1>cLw*XYo-{uCwTHAUlJY^w>bh6MMhvpy=gxZ#tD)btG9({f3E=sct)T(<K|5s1`e_YIHMP*AHz'
    'SL(-Zz~Jl0m-=8ztk4PD+Xn7MV_XOGz%ri|E+X7~zGX-|PXj3+g9TIovubt*>@k|h{YQYBVB-M>Y>_JC9vUhLzF_SEsd_nkag@uo'
    '&x}7ZF};?hWFR}G?zdz|O^G?M!Qv91MO8H|w4dyzDpppYzdKv6psF3{7@0J9<_-K3#`J+7L2OEH$`KN@LL(Y&xDR@H(#`pJwlC~V'
    'TvHa6pfo~)O){NKFwdvfHImVpL~j~vo6UnQe9$?T0b7DbpknLDMT6nt@eKw}cI42kaZ|ok`x~wXQJw70WGn!KV=Pm&O7kO9ml1wf'
    '>_bLj*I?|hwX~#k$pR$UEg>B+hv=wCzz7RpL--gQ+PU=_0l5v*F(18O+YWgwza{)lJJWnmJz?!?;)}Lb#WnoV-+zvv@X4qpuZrD0'
    '{L0j*hpyp@Ie&+E@8{iVFO>G7tLX1vfT*pf$J_5qgj2{&==LqW?_0CSH$9-gIYxv<j;n!cS7QjI5YBkjG%2Is5N=`{?rkTW>GiiK'
    'FibQYwL^;uueBG*qCw#agd<ozupoZ>IVrkUUf%HFPzPks1Biqr8zef*xu~!h9eIQ@*n$=X-iSn%bG3=Xw#CEYL7`wuB-RYIiEV#@'
    'V+Re2xUbXagfNf9#&0t_1bqH24Si0Z?e4)yr985fhl3IVf(7W;ekbdJ-m_FThLR=D8AxD)_Vzu^<Yi<_6Qcp?JU|1Ug7@bDf{vT;'
    'C^or~SW_bj4HCSLS(68V&1W*D7~h+z#rR+ay;MEXc+sT}lNIYcc4Mxy@Ih$41ppgn;qRBaQVhIE$B#9UjolCW5ryu@tDp8+2ql)j'
    '5k?N(S?PQnK7QmBm&wM@x;;!?v!rnBh6PX$<|I+<nU)5i45wK@cXKbGgCDt>bQS8PC1OEME=jVYPf?WyC9K4S(J@1^D`XkoR!40n'
    '9%GS)CTxQ#N$md7&V3DG;U$+!^%V)sKPA;?=y5@6pX$|7MW@@sVjdmf#IB;piZMHo@<N0U&tv3Kuzkq+JVVy3sUQ0K@awy;55Nzd'
    '_QTHXd)to>zX89q-$_e;v;`aJzy0~c|2~|i;-P<%S9m1au9=`c|1-&(!l6tooR59*^B!Jv)3yJ274Lrg@awz%?Deo)NOV2*OJ9E3'
    'Za-m&fgI@nm@n=hPgpCuGhpKT^kxxE*}<Rr^Gk`CeU3NzPYclRfBEY-UflKY{XNmK3BSKnH`ys7kJu>i0hvR*p1rpcH8!8bu#lN;'
    'ctyu@-;=bIId}ZAGky6($Lvf2JF+hwUB#Xc@_j}8_Vw7aD*wxq#`6W=4K>ZnZGr=D4h52?@TN#2O1Z(Hl5RWRJ$zB=;0xlM)e0->'
    'mkj^3isux&LTYzzl1uWpF{&9_l=q)J-P335oWP1y$&Y`8Bkh)QstMcRKaBFI9BGNrTFGZfk)*-xBcG9S-%6H|uKgKFzI%{KDsZza'
    'N?fcQxH@sgC0l&oK?rnsVVP@F{T0-Cs=5|tddfl#`UWNymmK2A_X|v{$G$>`91?sdJ#xr`4(a-GNbcqOUQt(fg1xIuv(0!m=_EFv'
    '8#zh|jlQX1WQOw!|4-Y@B7)y5W;>^Ns#KRhcDpI)H1kj=NfvRQ#<(tu13!{OGG!j)$n<2%e?DA4g0S=j$i0zXoRallBu}>l+)2*Q'
    '2Np6Mr)5l{^WGpu$DvTYxDaoKoZ%}1QTN7@3%mPKB`Ngz0s~;6yqzs5Qo0;3FeHM<fXTWS4kd^AV<C8YT4g6|w*2;zyN(L~pUbDZ'
    'e5y+?zpDTK*FW57=#=Tk%zQ?(sV1?5eI?mqQ_W-p4qwoGWCzzk1KaRg6|MXvf6wsnihW3!PIf|T!}iI9B|a&>d|3u)Z&Q*RJFg`U'
    '`~?L~NmyeB=sCl7gh3xqPJ@}sA_GbvI8~TaP<O8?aHBuZC_Ha{@l}?(qNKeFl(QHIvYLYCIc!I$6IDKl)Fu0HtL!F(VTwp@#n4c4'
    'dc;91@{zob=b+nbOOm!dP<pu{M<}0Osz$BJkixY=hJs?eBrMG?L#UZYRoBf~Bi1RDQopUmWkzwSw(g%LL#?KQQqA9Y>CyRxy|E<Q'
    'j%@o0uj-!Y(8HCp+n&lzWDtp6nb+DVO!5tE$}6M&+sG!Zl+`b4bCYSMa4Iu``AM~f!%CM>ybeo#mvqmRva!L-w0Ws}ZzYMDqJ6Vo'
    '_H>Mm)RH}~2PVK$Q%G9L4c-z=VE2tAuV;9T_z`MwaCxm5Tuu*2U@@1~OTvj9%CRDcCl?&krKW32zVhy~BIU3+_=dDbV2YPkmJyH0'
    'ub_&;^edcbG=dJWEiZefS-8{@%ris3UGogRWOG((0<M+s>6lMmX0<J+u(4|1#8dJxe^VJnDiYXz3Y(G{T_xX33fAb(_(UH*M`QBM'
    'u29-lzp<*h_ZQ1B=_!?DSo#t`9r=+|N|LV67>gYS@JggsO+F#oEtY0^3DkyX5|lXtZ6(Wt>(vX`m*UBEL?>IZTa~nMQpILw|3Do^'
    'XVFg<N)4dzQ$ysl%WUHhZw;nqnn=dT5=sb=&pu0*628v&pC3N8o)U$yPq%BLp_XVdOzurE<A)Jeft|;pCGRJfAx}D7oS2qWiN-H|'
    '-Gso&{)2Bcrfad&dv5U7ZdjH(yM>;eirvgfaiwhc*|cP1_e(Czt}q3m-(zKSRG2PU!c)`va_neGE{I0zQmygn3)aBnKTQwUiOo)Q'
    'ia6fV|MK<oyWNl5&!7K+)g(zIl<v(<7i=gyMxm_Q!}2w+Rq!b4J@}qfSj0MMQbCfQy^99&*g^b}1TJ(Uhc}&C^@`83H|m$zPVX0!'
    '@vTtZ&*0wCeWoSWooP?iAFTm=r`E@t{@SJaGo<=XL!-17(UMr4&icB)BLBG)>+1A$I}PQ^#~;*S!!Q~+ed|sM-R0kHZ%d)Y-tup$'
    'Ha237V#(ulC|zTZujK5#DwudY+t@S~&f&67Ip1sMbt^8*$q5R&c*sAQjrTBs;^E=xzuc9hdX6Z%JabbOpC(v6XND{}j)mewqqxIO'
    '=*PYv)dC?ORdCznAD|1OEttYGai$vp#%`LDx+<BG%o;ywr7%=j5FP5!-cSXptz;^f!vXyG?Ze0Szkh$HU%!FeKJrV(#;^;Y<9YJo'
    'nSRNOX|M*lB!fiGawAQISiX?1>ulTQA|$ClCw2E8`mu#6;?(870RVai?cm3hl|EGN<}m^35@cU0NYG|luop$H(!p`v-W~fED_R*l'
    'B*#*BR<tsgFQvVxIucW=l390zXH$6U)LsSv8x&3%ntBRB#V|Obxfz+Xq)PQi7OrKrpk2vlR@i0>w@62!%0fIv=gkvI^BPN<S4}qD'
    '!6Yd+qf^(vQS?D2cs92wvM-co<k&3q@?`e6)yGS6w!_LrqOIxDGI!G>V<)?Wp499RAikt#TLmn|J{P&4Y%YlBMgl`S2O#$GKfS@)'
    '<q(Lr>NN9=>=9?#_$m#1DmT+$XD3;}2MIgH$FOQg4}0^KRaO=y1fM1jDFhQe<!x1Mdo8Y4O*$U~d&J_L9Cwx6umFxLz=5Q4qfm*b'
    '8EiF=PGGS217OnW3Te+LDL^aQgf10yPo;EMY!@WkjnY11YPG9v=#@(|sA`%-5eAW`S|9AuPh69JbKO2!b&J++paP8xxKf1UXOkN`'
    'Oc$?Z1)M?JLTA50PR??;-WnZev_gl~FIS|nUDnM(CuRd82}v;1no49Xyr@92fg*<(<&}2^<Q@CngB5tCj`7vJNCx)XpwLEm<@VaT'
    'i@q-EF<PQ-C<U|{6K^ZXJG)MEAGW2bwlasp3jqDK60dZ%))XtEZAe!+-l31lU|=(&KUOrgun-TPtjm#I%7RP<`=ps}ZdIO}2(#K^'
    'ldFK@TtKNW58#Tn9^ei(W$sz3Ios4(Ee^bwH+l#DLaa=b%BHk;ZL-M0gu@F>B#T$J@8iX0qU=Wr%3mM0_J95G@$U=OR+aX0TN;&d'
    '@O)PT%Atn=cZYBtzWlP?erhalno?*cg^*DxonxuwpI<-?MhreiT<6FsO~{*)>mW%wou0hXZ7}3=ReM*hrsP;5Uq)uWDU0<nu<G^v'
    '5-Bo<d}C-amU5=_ix^+`Xj-H=NhFlqAXR;&U<l@YT<~c|(@xZ}0bS%IW2BIk;1Nn4iktC<nBNbbj4AZQG<wu13j-mwnC^QyP}`|d'
    'aMwdZ4j9qP=|1>Z47Q(5$>+h(mv+!?v{-X01zlHbs;~>YPYf+W6c~!8YuW_csXQ=VpjnXkWKE`3J6u^+mg004Z3nS?qyOq&He9=B'
    'O%4!-uEfEeC5j}D_K5VmoCMpDE7VEmH!K3`|C>IcH1^?1QD$<($kqE2edm!Bnlp^FY;N(4tnHNJU%tiH8W6xQcX>ChP%+NMv1#PG'
    'yUq49<0$eX=sY)ezFfz50D&Tx0L}p19SJ*h>(>iY$2ioomlJrZbT@n_ibGK>a1K%)UI1bTXzii|4N@vPh?obDo)Y`gy;IZQMqm=5'
    'Jt0p2kfC{lSLsk6o;mt-ghLehy7eNsNo@oD1m6C+1_19g&L%c$P8Gx#&~C*zv_t`1xLeTGfwLggola1o{*jP5@B+H2J-HWot_Mtz'
    '?#rFE$e9s~v9d6z3-*7dx<6S8l{mOat$zJ5e5%dW*qX0i4@-C6kShPSl<kscBR_S|q9xUl{nJ5wy$dK|ny_3;y`gIgYOUjy7~r;q'
    'eh16}HIhQ{ZHmD_Zbj0)H^W>9CQAXG{+=7<0B}sb#kwr1g3C2~d~bu@H&~Jx6x)U7rcxpjlK%G+d2c3`!778+XermQZmisHpyvua'
    'npwQQxEzxfJwpQ<@ibRACc7(VXNXnliR$K+hpJ$t1WY7eKMk+0M1k&t(!c27cc~*;Ac6f)F5Yy>xH>iQ{Q2SG%T}zReBCotEg%NV'
    'WihtEZSCq99?fO+n#ZNfZ!f{@y$n50`$Qm;74r1KP|u$p_U~SnBr72YBSm1g*C~aCb@H4hgaJp}JE>%66sZY6m`RY3zdyQD7sTCX'
    '=660(4z$%44;^xR$zDccFNjgxN<xFh9I=0tT-aiT=9d)>;e29nE=d~H9@v#_KR*1n(620(q68zv%*`&TnQ!n0*GNy`fQr8V_;;E$'
    '1VxEs!9urQ`UV!uxS-Y;l2y665%twZM<cfmR3H&b=n<iIG4<{75!iLf`nlTF$En;<4+<xihl)0tNQ2JYg705r-5UCm9$W5z&QDv$'
    '^Uka{ls8v?E;voWAFxQS_wFguNUUu~{P^v|$M?Vg^bmnb))5qN>*W2!p&S$4hH|@_aFZT5g+B6<u&J$O$ZVYlgQ5jVsx1}BFUHCy'
    '68)Q|8Qx>qmybm`iH<B#axb?iotGuyf2P+@-`~YIZa@*tc?RgUFb^uvj~a2*y-N3L1GLA2U58j4E!q1~Lpq1utuE#Sh|GgS(%TlL'
    '=;I);c&Z;+5y4J^+}|V?t1yB|ctksz99k+8q@ohVK$7a-bRgwJniM<0mbZj!dp&P<C2PT8R|X{h=}$C?%ttEvYaH(z#NEItmW-cz'
    '5-Ry8Q3Haoc91$F)xXENuS%Uv#(DE4aChD4f0zh-e$$_X5?!UD2NrtKbIZ8OqLn>dbJcS->-SyyJ;`#G+LtY=y-)bdkIWi|d>RY1'
    'RKefMb+$y_YxR6nn`rTgsJ(InDN@EO;T{A!*2squ1tz9k1dp7d9>qtO)p;hn)?3G;g6JrAIFD%$cCm$BkKiG>n;k_-VE{N&q5%Zj'
    'L<&76&>}xKe}wvN=XdQIO_P`iBHDlndJMA2)`DHJD4qgk8;T&;)ulBNUTx4k7HjA!3Y|#SJilhTA=tokzLE|xT-m&88ZVMocE@Ge'
    'GIbI{!O1Mwh6E3EIwx1yF(|@o`~<_QhK+qvVK#MS{n58E?V<dt1@I=vF%X`d*&;7b+hJLn=*m*KSSh(CtacKLOAIz(#&Q%ZWimmH'
    '$kLz=d|VFSy@~!>Qk#+eB^J{=*gzPrCY?c<)8e(bXxr<>dSPBqRajJf#oD*DL|t3!u)2dz*%8+X#0NK9Qj)3hp*eldMG-)p=aUSm'
    '|3dcLZ9NFhQ7~xi%`<~Dshm1I2QVC%*&aAiT9t2NN$1ZkE1H<h&uEJ&f3#)EY1|)Z8G%wWL(6E=@<*lVQbMPFTYem5KMaZ0Lr1h7'
    'TFoV0sRkRLe6LbF@T%vvO-^nLGTJJAcstlFt>^4@@%in2Rh-`YrYCgu7GmPuR-*%2-c@p{jHC*!E-TqLM%@D}A5fC(b4LvlQ$d^H'
    'p$*jumSD;&3lJ5k(37>_0Nx87kkZ^eJUrg^ZyI6sj=<*j?)I<yElT8Q7!-|(kMx!H-{O6_<O#ZQk|g;0znBuAu+~{9_z|L|k#o`d'
    'uiK~!b8q58SPnWBNKNmo%T~Bm8_ra)>9Q5G#p3?X$)(>p&(#ifV1q40v#z`UKrZc)HwHcrkA+L{1ltKu`vdaZx{Z)MAg&jSq6-U@'
    'sv^fTp^96IhEXat1RGrB{$dCY*IHMvP4~8sf-oFY_6abo&31fLM?Q4}=?qR!n&#N_tNIU7#FvG%Rt`p<IpO4RUts4!?weBY9q63#'
    '=jJ}>=zx5cWDEsA3-06DgYTx>{|&OIHejWPBakzElYMZ1Sy*maqnPuizACErnv%et+~w*;`9!VDnyMM#Jr2#jyFl5?yq;3Jq5~cq'
    '(yFq8988&n3@b`3H++h(z^3M5DD(nlu9Np4i?ACWlxD^Cc-?AVxe{FihK3QFfqry!xE=g_uwQ#h$FM!N1|6iLvu1Kgm$GRUnDRb0'
    'f$@kyk+W{JUKGx8lR}-O`Q&v)%S#7rMnjO5eZu!u-vmoabYbyGBpf^Dj74tJD~^V?24V*FLBNnlVH!3vKGAx;20ia(FW)Vzo1<#`'
    '+*IYb4<QMwo+<@+ZMEDe0DmA$<>t`PLwB?ZKv4~BQPAW5Bvr%|1!gif8bH@8GDV?96jDH>DnpAXDyw0Gwy9IcT3`KV&_r#mlbAY)'
    'GM{g}1~Vx((qwr4Lf|CnBdW=zXwhXm7m+>p=<A`ocyjS}_H9C<f1q?JC&4i65uOEk6|HAA#9dj+t>7}0AuaGkIOx}3dwX*p86pzZ'
    '<4`~iR2A*v^DDSasiG!fLyRCfE&}tD2+WsHV9_R3P`n6&+15){Qg?p1aSr?69QD*a5o9B7ky)TNTq_vD7Cl}D?|%<~q^Ke9gldb|'
    '-mX7e1i}%_9(NZTX|y|zWR9jWeBKUj`nDBcDuNh_BO!NgDL-M7I8&1R9lI|D8H7Ol7_10mt0tCeP~m_e2qX;oOIsw|m1Bk3mT~Oc'
    'r8F`i(j|(GPSGe(Y+)d#t_^1pcDEg1d6GMfM<q_e22}!u!cRtusm3xm`UP_=nV#rj;k2rUO|DQCQi(cVWwi)k@L$bV)Xv8!P@+)`'
    '+RJQbqK-OaRMBMfpKuDOHfTYmLKOXg9PkKDgQ)FRU!#@L9zZm6Z>p;~%RJy;xxiY$q03t@G*L(OQ;W{ehc2DMXGuOd&hMn`oDgl>'
    '2qzZC8cxm*7i4<F?w`Ls<G0ny_qP=dC_A9FEbele`UX)psXci~XGef5XGsRi7LAFC7~9f$eqrwRpu_v#-h+$hs~aCEw!bflP_gqT'
    '4T~;lf8X9u5(#cJ!u{Kye_jZSxDW`IT@{yVzwhavSl_Q5Kyjd8uTjaS(J-R81viNxeGVMtG$qJYvWDIy<t}mTcTT+5>slfQD*GH+'
    '^T4s{{0b>+q7Gy^it}U$hgxfva(f%!kQUY42RC!_FFO2S6dyP>cTG7;6o6gHzi1H>k>F;5*{e``pA@_#br?)@WJv@(P8@LiUD!Fn'
    'i3*+Ub_Tk^l9v9}`4X)H2A~uv;2ZF0If^!<)#$=1NSOmt!kWgVUvaeL34;Knx|JvZLP9^y6uORiF#0CZLzd3jNid{J)jSJU)4sUH'
    '8S#w4q%T9Ju;-UjE&?;|qBTk!t^qurE&L%-prV3bYD7H=iw{y69o4lAYJ4HdQ%>eQwqO)`D4UU{e;u?QML46)8plD*srHz|-qv&1'
    'h25dnJP$>uUMy=-=P6Vm##gVt)W;e}*SC$T5`Op@twl-VwK5i0Vy7dos$eODcF@f(L%V3I3@=2BVY7n|n^gn4IJ6YhRto|)7!>FM'
    'nB$qYj3%v*^ZfiPc>2q4L6Zq~vCW%CZa_lSNj1}50!jGt_4B*kkK50m|MBGC?_0nU>UwOQFN;wXf`kV4&WcQP&i7zQ2Gr)lTGC#%'
    'Tzvd2Ic~#Y@0W#w9$#K-f};E#9@w(@Zgm8bxAGN5k-@GAGT7C~>?}7&aTt7~R@mfOj9RBb#9|>+$=AZSa1U7B1ieZ+Ij2mmoA$6o'
    '?I63+#9lYMGzLbY0V}FWhc;bdqgEw5#1|@AWB{sYZLq2$Nr7=$qO-uYYfGOk9xhK7D4$G}16ebD!GT%JCh-z<^qnT<(9Yqgz<&`d'
    '5d~ZNw8By}3|9S?%q<>jAZ$L#q;jz_q;cA#b)M*&*gO_kGEUh7Ayjo_m}E(5&X#bi@zeq90oc_0+d5D)V&@I=^~?YaY+$+K*}&{4'
    'RJ2r(pwP#gkFY4Vq1Jbd`C_QBBVDKy@TnVlrV7ucN2s)^Q>0qDn{@_a72m@frQsotL~q1Xyo+UdE*2XQAv>E+S{`ClRJlS#AQf#a'
    'z@rJ#OAc!uc+f^c8Aev8q__`a`>wptW^vlfZfqys{asIhH#&20bX#5xu8F&$#!c1|2aOvNt6;F!GRZpRCcC=ie76{QE2oj>On(f`'
    'L{=mo&75|e!xS9Tq;wzKZ|dw27gE?Tbj;!ql=Osn#CmYQz<*lax9Ka9Q2)O6bpqXq?OcX<>oA?0kjL6ad~~Pdl0KI>F9cA<RW-sa'
    'F&5KpN2XX%8Z>S)c2hgHSo-F5qqMt3$77#dp81V~IZCZZXZZcxHf>6>6J?5d>6mjn1Y0GDz*G`PDJk{*Vb&l6+R)H<+9y;DvX*eO'
    '!f<b-^_V0SvWz`Hw<`2zEg(UmA~hW-`El!;u3{HxH+>en6T2FACpIxj58$oZ7O)&>c~N$%-U``N&$5DvBkC^wuI;c%O6&JgM>8pz'
    'Emz2OY@vrrRWd5IL$6+Abkb{s4<#8QC=Y8PfO~wS9q=jDRcO+osgbP;AO9Pa((_;>E4SBl55mv_aEOYbI#$Xy-dx2N?kwrD$V9hP'
    'p*CHo+`&r7p)DWFW+GicY3fzWc0o?H3~j0yC?#x*$s<ZMR_@Lgamv|KMem)*Ws)+D92wClrKp=hp^<=Q#i&9nsKc1Nvl%ot9kdz;'
    '#HmVbF?rVToxJJ^sqjp{9JIt9JzDm=@33}vQ}$NOS_+MauI?PDWP4RZ`an+jXdwS<Y(q1$48~**9W;Y6#wgW4KGNINALud`j9{V)'
    '(k5cTy{)De>KdDSPi!ReHTFd$|EAEfG<2ImZM<+;WSKJ~hGRnpf)_sEOjp$u&I4Sb^E!<sN2wSA<a*$D8r;IN7hI;vd37gWA+5|J'
    '@2i)m;Vg=tC4`#TI7_%>#R}JA)2+iX&lF<ei|B00%X}SWl$XL*2;@lBG5g9<Q>{Q9i?yr}G{Zg*43SOeo{OhVBap5zEK_!v6IhE{'
    'r17f><a`<c3@&|j1`AO!xDeSn_$UxVFLIWfx_De0{iz<^xuieV60@1zuRLldJA=|Ss-^)mPp2^G%gOf1U4{%4azEBjCzP$=SfwJz'
    '!jL1yfY43IDhx6vZr#>A)KQTObHWmrP!I!U5~=n`Nu{hqJtcj9=k0K6fT>u3DR&otQTpr1D>Q@Rattx0oWg`M*C<+jlYj=~!7qzc'
    'k-MKR95Y~;uE<S_g;FIF=8*C{Vdz-WJs6TpNYjE8$IBSI;!dR5&{>Q}SfH_LINK7og~3>HWJ^pc^1JBnEZ8BOQP5NB0G5_#T~F3d'
    'v4~&OKDKF7FR*VMXD<hY9(QT+U*^CoY?#o_s{Dmg6V_$|d?3N`Rhry0;$sZ-X2LMK0tHa{**M6Sbfd#klvGLMd1ILGcV>0#1>L5x'
    'f2@F|U09SeT~#xhn%PQ?qC#1u2KhnfGi>buD{(oGF)$Cf=H?SN?zw(|zJQ{9jUD$u5uJLk(VLkFBSD2HlBYh>#j1Bhqw+X8gd^#('
    ';<g)^ipWvDP>#^xtf-h<r7AWZn5MC+xB<N>`QYOnCNjyPokF@93&Ub_fXe>BSE1-6sfLF3t_NI^$eYb_Kwg|Fp%C+oc8XhgSBz&f'
    'V=1b9Gk(ZRy(Z9+N$^1@_B!#3edQ~yM-d*Rtz)>GI-tomoQ-$d%3E9MA@f@Ut$|Ll5@~nVdQ@upZoz2E%{l2PNx9!NMZ@hS5D)Wf'
    'K^`-l|E0BG3egTErRR#R<qVgU#<sz3ojmy0*UY$ePJ79qdh$^rGNxX|HAdYlTK-FlS9%wr`(O_5zpc$GHfL`YK7a%f;+t}C9b5LI'
    'NQK;w=`hdt20$p<Xy~k<K|&O86{j9)g!a1)A+0;0bcKZHNnE9shY@mX4q6O}8**snvMVr;ZbK|sP;N%yVtw80VzMK-woA_{WIsxu'
    '#;8Y$YYDpwG>>C}QL#JA6*)%7IEQ^(<Af3X%3X9<P66qQI7e3(o=`K+QBLBTw{E*5f9$3VvCg(iC@z=&cci?hd7RzO2U?gOb(i=l'
    ')Fke3YZw4_7|i2X0gvaCO)V0iB)r^|5@!b2#L%pE>-IccqULM&g+c=sU5ahw%)@O@*fWf^GvKF(q%V<=*^`F|MWH(I7}zw<V-+mN'
    'IXxm&S_IyBSKhs+Cojunj3hvIyHk`wsdYW(FcyVXv}~s3ad9c&mS8xs^CmxYLQyCNfYSut&3*@$8OTI1Gem4r<fECvl>&O$Ld{=6'
    '_&kipSGe-_B#pV{P*9eMPG3ap-s@vBN@d#HtGU<jMzAt`w%nZ!yJzqmw-^VYS`TbVKdk*<g6T@;v#q6%8PtHz3*wbRg=?yQjVF^b'
    'DY*<3gCv`~+9$}PorTO!FBrLgZzJbcp3|z3Ur_~KS9YD*3PE?Q%4Y+##K*~^W%&2{L0pU{Fug^k#}FzNt-9zs51HzFWE?1)`56pr'
    'e*{;6H`QGWBe6XP`j*;KHR>3sOL$irROcFxG^<oU*r39M&a(w2*a7J0Ua>vCGIq~$*)a!YYwaROx9Q3Jz{)--AjT~Keh#wZGzwJh'
    'S($(R!>xv(d4hLwmEkoVYz*i5WfvOfiK}W%1Spzdy?xYeM@ufz15Qb>Tz-|9-KYd7)=SH<MUsQn<pipx@QAQbH+sx-0D{nJ-Wm<#'
    'h(r=KiXLn{`kz9&jgd2&ooq{SCBoUI($AtK2x^=*B1FMA<ybBgSDA-q!>I{v)#gU6-MKcM-?#&3$`0`-5f>Gf$gGS#Xr0?*<b>{&'
    'V<@ithIiWnGEr99H>jU^`bd6m)WU>GhX=Z<x3!vudS>y}BJo1WI>cAg+29l?p&mc));DB!Ypv?KxZ9DXp5KX9Oc?0W88w)Y=z%yv'
    'MCpC;eCGX!pF15>Ggz&`!@>v$T<oGi%K};YcIePb?f6l1_C0UfRfFY#g}A^H(6S@f<H7s1dFhN~XvOVj>BALqmD(N-$ofwEIeTzF'
    '=<~479(BTIEuHxKII$Z<7GkG~WS(vrfm$n+@Uijgu4T`bWFM;!2;t@TG{}V`gS!?3u~a!p=Q5O2XOZwkPZyy)t2oQHttnwBVApRd'
    ')PJsKFjvH0o`>|tTb05rN}W<?)V)>Qx3g%DNRZ`^>5{fXOmpvV{LB_}n@$l~73}$uM)7&t=te^u4FF><Tu#MRMQ|f28KZ@L-E}pT'
    '348||ZAQ8yYOWEZ--hO#S8oXZ>aAfsO?pROr+$Y&xRB4pnBZ1mxp|_}`E}E)hw4Bnkn>7(5}te+%)w@_nZ2L?ucrtAbYM*~#<UGE'
    'A22~Ig5DRMi9S#E-h9#tq&%2ufL`w&<y_sBT~8sH1I@NVraisz7wq|uPF-b35|1dwkpcX{0qv%|{fXk^U8?K{?{S16r?qBxdB^Rx'
    'T~#u2@DEW++38vwXbr|HnS1cM$vInlTr*jOkrpv1JO=f)UM+R8LlGJ@h}YeK#Vn@`A+qs;I|?w0^QeuOIBp`>>Yb1csP=_Iw+9@|'
    '9uyk~ty`>Iz|0(yO>|0=HMBn-28Lsi!J66#9lC_z^m-#>1GWM!(plxWtqc%vbc=#Hf5P@_@Q~*w9p>gEy0mfKg3=;QKn@8lLu%<^'
    'mogSZ*Ihv?Xc?vCjDXY@{%k9Ou}E_V2`@rj0Muts^{LfCJ}R4y#+yAPUoG}yu_$!7gl4@t>g*5`<c_^%^mGvwG$?g`nVDY>w$Zy9'
    'aZnAYW(6`mla%(lwLrjTH8kENRM-r@8DNQAI9@~DT_xiq!?N)6R9Lc^ryAKe`nzuu?oLYA0Xpq%^;$EqL&%=8#cZ%f*etwN)wh?>'
    'ZzJchdF<%qk3|x4<p%WNA-;iNBO3oEG0&dng7reJ=v4Ln=Z8;?jYoYw$CPgL&b)wOPM}ctNNQTs5+B)x;A4Ppczm2wwN}f}$(1m$'
    'R9Y`Eh-Xz0eMxJD6Z;_SSemSmLU-o3aUQO440bP9)r}l%*3&etbz(E%b(A_bX2IN``$mpohE{Mb&tl1`Yq9rlc^X2=0_<h_3Mf|-'
    '2Ui$r{#LJfMN^E@zo$S1aX{%!c}7y#4Y+&8O)Vyx(@^gx(jH-@^&kPHyXWPi|0LcQ-Avi;W})NHkbpLWvFvEkKq^;w#MCgHx{)iu'
    'c8A@96KwUabP?#Hi=B6dj{ekb^}x{5L=}$pEQie;Da=WFl8uSsnGdaL0pFf7pG5(eJ!gN7oyz6LNOH<tCW4LGCh6ZeauHn#H{Ml>'
    '_#~<7!m);GDRRM&#DbF8KN?RI`Nq;)h(;-;znMJFj2CKO%zVtY19Hh#6UNPj9(QbKhdaXq?2Gd}lSbs_L06|?l8Vm#Y@aZ9HxRT9'
    'eajHrvJwB>oc|z2Dn-`{x{4S4*bTpM##QgRKbc|q^z=T<#rlqgnOl4df+ztfW>BDighGgPLX^>g<;y7MG8|=S9nwKWM8f`4Vsjj('
    '>k9%z2x*5~dcAm`sA3nrX~64LsCtM)jvJ!PO~x?};Y%28T1C?AiZn+p85g9PMVE4-gydB-kQB6(yc|s_z7?_Pe^6c!y-LnXpfHfA'
    'Y&8lY^Fvpv)CvWClEaL1KQW!5>O(}^CUmybq3NW8^Tq}XdX{AOB>%C8>@YNHoQRFq`$#2ONC1;?Kg8lT4yNmZ{Uo?i$fyJW{Q!!p'
    '@6Y)8fjd(jl+%CyzSp6Kz06*Wz#IgL6mMq!QWBwJNbV7;?g66Uz8Yt?Etl3+wl#_9d<M5xBtV`gHiPBXf>v;NZw=wit6g%6y>mO*'
    'LavU%Uy%fd{R1<5*o4vntiCLczuwkM1EAZd>=4;D5TQOiZM3|fx}F|qis~OW<Fmh}IhA&p5qlKn*vnYyJi2lC^zL+$o13cy4*Wm>'
    ';q5#}1l`Pr<>mFI3=gFK$bYI9qguC3-pjp=fjsQPrO(z{3iG=Ws?o*PPRtylv8j}C9m7?UQs{1`idc%Yw@Fl3&-KM?mJ2B#QcK!H'
    'yA1=YO810i-gYBX^v8V!7(WUtFFCvp9hQh?gf=0s9&H|ZtO;RXD>`K?_{=Ad(o)oA%;il7P_ZNeA7f44LJ#+<9K#&E+JE=ui(hhi'
    'g{buw<uGO*9*UCr>lOhBtB3irkS{hAGQEqGETw61i*jIvh4@+7FNY>(%@rUt<V&dTIhd=Jd;azcxU>^ObRLC*VWe<nOTj)VWQwIQ'
    '8IX2plVjKbp(Jvo%HZ|Y7}-5v5q4>=bVIWBgMTtqVxdi8eRp&9y(MYxD&wW6A?x8{%YhOZxZlyELIjs|Ysh|`WtG^y&g0Os*NN%g'
    'vm_k_<*4u_T*K_0kb7`E7V<gd>U9tHXl@&9tg>M!;s?Uk7Llir<uh}dg~eHvN$)@f8~$cRhJ4fajEPnrw8Nd_pqXplY4q;20v)Ks'
    '+-%3UP?6Pmrn73IUH9YKKom0&7ln!N)h$;rU2~1GH|0EyfsT#Lxq5{276N97Np)>bC2P|5yD;(!7<p%~<O=%T?Nl_St|YzXRLY71'
    '7$xQ1Sbt~9F2|p;NqfB2vi9oz@kj+U1AA&$!>lb^w+h;gG%!&8PEd)sn1`uU!G2*uAVZY0R0Qc93i;$ILaoE&O-dtz74kuDh2*H4'
    'qS9J$h2?tq^{7tG7anKPI%Z8Q4=Qd7S>>QKH4Z;n9XOgsLiR{6fMss=^<=%}8n7(IR9a<(e;l>4)RHc(uC#4Xy}SBxDv7Yf&mRo#'
    'a3y9a=m&*u21w!&K*oH58&linSj&-lQN0t%RBxL=QH2{P8^XG#orTPp8&Mdc3MOB6ogc2)nWny2nviMHMJEB3wSyz3cqdJgWt&k{'
    '9W8m-fmM&8Lqo7<@tqn_nK%oX)oMswy_7(fIe{RuM;`5@+|;cL1tY4frR%9Xh-4YX5^EI)4E`+GNOZ6xwuVFFQ&gL!gxVYn(ZXD9'
    'LkLPueys^66<9XMGj=yH{n?zR+~QD*0-n|GfjOLkyb&RHQ0}2ii5{rq<x>-$*5xumJufP8l(uRwkc%||`zzH88X#=2C~paKqzn0F'
    '853gQd4>(+<CM*Nn5`B5k$oE6<}4}AN>DopfV;%6ocajW4YwdTBD4^0%N7*Ly_?v6573D%v9Tjeu3}^8dPyc2l}g5J?m3OVFjAB;'
    '%CU|8SkUaF+6-s7riivhHs$yXI2uTRAxg-E;X48kDPKb^iPIoorwsZ>OGUSGs(YF)TgFzFx*;4V<4TmE_~56H?|#~z!5CbZKjDJ?'
    'FCH0>-iOT?(}NIIPYTq;dX4UBPN)f<(X-aq>F*5dN~P~3{N9RoqI#ANTp#zf|3dF<AoB6{4Cr0Zq3lNeE6FAiTxpZHmQ1JX@*nF#'
    'T{j4NcQ_+R8qch=Q>Gpdy?>Iq$y-UYf?lM;e4jRRemh62ihQ{ng+Q^vfK@?Lo2+WRa8SJW%K>*y(3RFY4f<68lfAc2e^jD4xtqjZ'
    'vh(^Tn-RmOA~9_)x4$^-+DWJajE_Lu1&XZjSPj)<^Jqb&bZ&1;q)SrY`TggIPhQ_dN0RTbO$pJp<y(Tmd6jQx#8jiv$$_&4cEUd_'
    '1<gie1y0-$az8iR{n*70QdK^QE<;D@`A$!4y*lRp5=oeF`hWZO4YGvaW)|_W4%qA0ugiBNyCR;69!*b^a+{*Cws{gv0|_|yJA8Pb'
    'qFVm-4|f_jy%XD803vrGU5;Eep|KcwRgBzp*YKWhTlD)fR>7xoX{MAtU}0{cJj(DRH!on(h9>2)aXPq&ShooD{ESkt@4B~e(v}b9'
    'R+J<UCKy*BO^yw|y}!8<GcpUZ@yBl;KED6`r-w*qn+!pzbD?iUP@fmdOfkx-YOwV3b9bO9J`t1U5hg+|fDN-F6jdRFMi#Y^Bm++|'
    'ZJSN!=s+EHF+&ZVQ-9LxbjE%^hqk_7mJW8a30FSpjqI+T^KaOMw8qZc@_i7^LF(e^NQ>*bGk3{D5JzEE!T3NoJZAy4FL|(^=kC|E'
    '7qajik|S|MdE)uS56ep-v6K=YX9Gbn<Zg;OMcbpveXNJ!fm&~+k<S8Jz2r7wO<9w~QXEqk7=lu0{S#2ku*q6oC=CUh(TI!lbFpUx'
    '1f`U?O&hVv3=XZ{#3rWe4pyb{8gCi7U!@<6CayNc)De)FAU#R1JBqc11NvbMCmJPCnAF``cZ}u$Wrl2}<;mBOywKP7q6z}3WC>gm'
    '#I<M+3WwYW=p3cmX49oeK)xm0HaHU4Bdi;=k1sXSw)-D#1nsivY7@2s!1c%Wm&U$xROs!a#WT7l1jD9&k({;#yQ!ys@Ji|DtCkyV'
    'D+vWKdey1tt6h_gi~E!G@Oxl^ynTCDeoBDL=b-dW3<6Ld|FOG=Uzxi6XG!1KN_u|lrv*IN<Z*qTN_(Md4_#Fw;KB+pZf8ckq^=Sn'
    'I<J9rf+!qal`er2^V|LD97%mI$A4Q?W*ubfok2T32dxqoELTmp2g59~^PCio)p&F@QRwYE9PF$ond;S98Ez&ivfcc4gXmO75fWkw'
    'EDZ$Q)gx_N`(8@)zNO}9aN%iTJF>N>+<nPdNH}z|;pA+XN-J+{hC;%&y|mcZi}s;-Tp(h4MN`n$co_>|0e#Te&`6PT8o*Z_1TH=m'
    '8nz&Xn_>%2>4lf94v2x#%1v9Wrl%SqqoM1Ra98GXf><QnSBI!Uo0Gf>EqP+KOzbLK-a9{@lxkrw0z&2ow<D?i@dt$0iAf2N-e>A<'
    '3d2vZxB7@f>V9n9)_^B8E2Z7?KT?O?wynb)8u6$;C)%4NJD3&CB@XkSLo|PV`1Re_2jZ4a)R=GYGk~REw;vyV(}Pyaos$l=7En}s'
    'YX+0U%OaEw#7*g;t8&bfb<&gMxhk6+F3IYWtbQoMj_od)>XNB0nQEp?l?580<4l+-r<WzmuEu(LA)nIf<V7zj?UK^U*gvV|R3Q#D'
    'bB;<e^e>t0lF2Ta?1zAR#G{`N=ehdj9c*YHX0Y5x=EUF(k|~+16z)szJa{?oR%g`anK0uj*;Vo-q;s83b-5pUF`2Gm&3ERLJzXpR'
    '_UAAE`|z5Hzr~YM5=UOaHS;FV|4j0x@K!$D9Y!DgJo094nV&yi#k=1={Q7Qxkw5Gf;%rX+(wASh+fNwdCfAwx^x>z!fBSU!gte{&'
    '(W%YZn`M0U_W#VEUrMCI;CPcie*5t8{qNuZ^4D(yoB4zH_e7d8{QgeeWT%Kc(i-CfGB@!(dvAUGM&dG>J#=&oujp9rdy<wiCF~zN'
    ')0aO4e$Sj9NA{(otJw2FzORViz8-s4<$rnPyX`C0%D&qb*&obpf&*{P;P|TGI;I@mSlb;EI+G|Jd_kNuC<BF{^5LJJ%}uc@q;}^f'
    'xg>uZqhk6+dH>1NJ$<&$39QJF>G(%D(rzhNNN3gh52HM)uwO#<E%^*v8B154k#gTkmXWUg8A-l-pni(yZ+1nA3*9W_i7T$!=lc$+'
    'ndT*P!BuW<vMkP1)wM9wQ%=P*npV)B-zA59@#p*fk0tvG9dbzUo%F~d3p%9h%OSa!>w87>1ALUT&3HEHWKxuLF;r6BeN(~64CfX8'
    'pSGDr1i#l_bF=WNQeFPo?Z)UMl7~8JwikZHpy<<cu6_>uNDj%Ad5q^Ru=VvLC<(Oyxi`{_OG!GhdPu~<KML+7=jQ_p8IDu8zTu`P'
    'Sbrhj3^~JB1fuSZB^P%0qe@cg{RIZVKzTb`P^6@lUtmZCj{%c)FEZ8TEQN~jt-XUc(uq1*v*ov!+;voV^IbmG<x^dH`BnY*zy9Gy'
    'L#IqPX6*dN#RWmCN$g->Nw(NjGueQ{7c?K)!8OppHoR6vD?iEKGd#Rv9}=b$rE+ZhWWo}k6kon91GM+M%Z;7a5(oZ*f~F*_F$46R'
    'VLQU0k1abJ2)qNi51cB@DX3Fy6}Zu#XVSi_E#s>!bwx>g6)0yh4rDb2&2!j}P$#N<5UES{;a1sA2*VVS+=`*0<n)MxR^%gj9nV3x'
    '*Onx0d!Y1kMUGHDJ*tYczX547q;PGJp`aKq2}`rf5NhU8)pc{$h;<63)NgBXnNeKI;7Ex#;RkeZdkRW5f8V7?=NI<Il5D$rdqrO#'
    'U6|<5!<Dn!p2|&R5CvCS)<bWtjlv|~z^1%1+P{r#(n?wVqBb{~Rtl#wBbc95TR5zA3B~KM<abH;Oeq^1yiA*yy7yLClk0HWSkR7p'
    '0n;%yQcL!{9+&`2O(AI|H+V}hf!#Nfyq@7T;zy{#!R57La5+67fyG=_F9|1dD94H{bFn+mbgAi@q6V<dXGO|kaqtakjldKytt=y+'
    'bp54F987+d4MrpA0Ne7iXPSje9l<;^^xHMh&`UOFr6%B7`JRsX<YiXdata%(=1n{$5A!#bQKTY)-KVfAnbB49y`*4`?u<|L;d3-5'
    '-|PydUG*EQntOk-43nNxNrt5_0o0KnNu?y|`i!yIVF0g0YSrWuqTOO?mX|<ncqT!aBhXf|Jh)!HfPE>ROh<IG6}weQ3nx`<X7&%%'
    'VRRP#WTDgm`aU&8KD*2|{_xgdYNm-~j4Yvq0Qu~*WGUh6eE<33Q|l>F2>W!qCK_sq7Q^J;1T%gZVHMbU99r^zavAcZ!^MedNtI~)'
    '($`H0oa{gNMq|1bJH6)yZ|#O<xwBj7*{RsgoD^5ecArg4Hg><{vg`^|5c)k<Hb;f&f+ajPoiE3ZhU9{1q%PGOpT1xXJpR-4aGluf'
    'M5l=3E&VTFKfl}kxc&V3A6QM2L_+D_+;qW)vSSp=sy!@U^I8RuqTYk=NrgqMlO`1;>DjwzAdelyA4%XsCvtexsa3D|EPJDViS6`$'
    'F&W<q)%^_a9o=VIV%?ecRQ=H!z;|kWyy>r9nm<FT?=&<@YY{Dp#p$fC`z!LFJF%`#Pj^0TUTPX)=;sgE+}m_-7a5i=4}rZcg%*3u'
    'zwp{Hi#3WRkJF)ajXl1Sv-hfC;_+-_(^xo%%R1$JubJ1axGX0pDCpuL|D-<NbLZqEGAs`dPq)3h+V>eOc{7ud95I4`x9q>utJf0z'
    ');RER6Z*05XSG1gM<v`g`3L9%X$$7COw8&gfU%pVw63b_@2TP^Eft0;3)V9M;@(hXW-A)r|M>00$M?T~e-U55frLEr^~YwX3!me8'
    '#^9Mx(zRa~<ZBF)CCkk!5%RX&6*Bc%lfrCL+v}kpTeu8QUEUL{kov~xX|IFxQC4J7xo^g#noBTrsUShyR>7_hx$FlAV|#b3Tm9u9'
    '78N&gsD-8OtZ1n(|Ac#CdL&3yg|qJP&F%@Q^L80_Yf$rKh_5BY1H-t2=00MHqEFn}Sh$weT686!S>bps+#(&7FN@9;9b-=<&1)=a'
    'UNzZp2a}}SM^0T(M}Y&CxYyKzXWu8yrLmdc<!R_|d!B00vkz-E)v(Il^hnsrHl`;tJEViHnc3L>$en+*5aQ8XFNHxj?O~q~cey~Q'
    'E#PQ}iAH}^Gx=Fh0ersvvfY02DzS>;!Tf)!4>0}BtyG}M0QHqlHht1bZQ;43l9ACNrA#~=06h=A<KR_7^%TL^OZC@v?|2Z*R0Vb&'
    'yiNRj;|SDO#*=9?F!Zq!=AXr8Q(JnI_nhKzOFDm#Em>tFQj=s-IymlVxo&d)%Ym<hD>Uzd63ja_+mp0gyCQ>@Jm8YAuN>ea8+HDG'
    '0k>gcrClSbf%oPsBYaAu*Q*?t4D{iGJAxEz#18yt0Uu7j`VA?5a9x*pmCltBI#g;6Ritt<9B`;7Yj<T$)seQ>J5M(NNyG|!bcxq!'
    'G}f6)cd6f%UVhd+S6Vmr->qX`j4=9sRe-t2MfxX$Ka#7oo?V~EGve+SQ{m1X8uZEsSP|vEenFC=G`VH<(vmK_)5fp{vR!)sQ|>e0'
    'ozlUz#CgE>O)hHK@~g@OlVf_uw~#LKb#aHW#bs-<L?R)i4o0@C^{8LSBv_O^x3}&I51_t&{qXVckN)@7rUb8=_-`C-7_xUTN{~Iw'
    'r+c67(Z@rSgYU{oMZI)`&s)3S6yqc<$mjwvrps5{XwQ_xK<14>GK*~@T#GkiiWJ#W#5sqg=HwYfq4tzw*E#CkzCC#Q<5|}-LF{9='
    'RYB+s`jJd>MRgHW0+W#PC}O!s`|4)^+91}<9_8k%p0!8~_y$c>Y42E+5VtZ{a050Et$sQMs3}XmfU?N1oi%i4NfxzF9wB(cr2Kn5'
    'tYzmhv7fKI5qq7e$wS*{@JU&xws*8`0jn6Y`C54NX<YJ+@8pf>ab(!ghXpScl!Z6?@f?O-AdhH7g;ONdkkqbDLQHpUw*{RovH~ud'
    'JHn6Oe4k~?3QnbBT%w4-@$T~I33~Fy?n6W8Hr}{1?Df3s-p-KeiC}q7KW+pfbzwa;4VD`nqx-_OsOMVbrpFXRBKA8srJYiWMS^y3'
    '4N{`@76J{>zDhu*1A{jYd&L>kMYD}ua2Yi0QE-r6QqSp^kP~;8$=ss^CBL<D&F)yV{L6d*1_>f$;bLJtu1KCe6*C6iNwNYmjKdFy'
    'ajQxqhRIm$^Q0Y1P+V3HBh|iqKwXV=W2zuVOKf*JnbXfCI(O)g;c#fRv>|Ic!>&{|+0%Bx`|19`X5e1yVsI~N8CVThvT7V;ZO2l+'
    '&@GNEJ2jLHSVL|PZ*<nxSl^zaF>%6eQc5N1$R6vU`mO7mH38qD-ewtCLy4vy_t_lU*^bJI{+8AjMsDppbRtOi05nhJU?^5iH^br*'
    'jyW95dkW}2R8^9YLQn0<;)Kz((93DGXQ?SPJ5HCHv)3n$jHph7yu6J30;y9WklFY_(a|u82%n|8=*}^bhDBQj13N<SEPW$8LFrOx'
    'AeV%r^!A0MnDdWcR4&Gfu61!tE?yp&tBzk)WA!K`SoE=TSN_Sx378BSryl%u&rn^VUrY;*RXaw?H3=`dy#%xOvS7nanC_kSz0(H+'
    '`C(8jE0rWGjSVdLG=pF!Y%pZk3JOoZQpwKP7Y;udJ^!O63;7GtreR8H)d#wdJyfv!3d`TKljGoJBsGf|d8{NfSb&-XQ($nP>BP=)'
    'L_;{A7_g@hANkkq$A{k*`V8iLBM67Z#LX_LnQ!n0*X<aBYtI{W@A2<M^E4((919k@_0l&$NjT-uuaZ@{x#`kZOR8!y-yf~(Yga(u'
    '#vH*;kOckJran&Piat;{vFI6ATPKt@QOPiY^|ZDyx-~Qt2Y{giv#;Rlam2GOJ(5dcX~Iwke-Tm*O-Tcxj~@Sj{PyAF``<r(|H*Hh'
    'ds9@8T^7fYWv`sf+_oTNXf+5HMow)pf@;*JIV5OBk!l77vW&4bi7bFk(>!nT(n`l-{=Y<NGfIuzqKsaahZkm8)Vs^z#39Us$^&3e'
    'Wc^`d`NPM*Kl<PQ>ST;G%z`JWSYR%U_8g771Yx2Z?&LI>h#mfE^!)I{+ZGk>;~;?PBk4Ixa8amz>S!Bv)JQ%P`=|0lPi2NoV4{FV'
    'k|agPQa-9lk7;a$OX$1T^Cnob#3X$wo21-K@*_p1_pVw`{v0?QU%bthEx6QG2(T=dkygdut%!mmoood&88g0HiU@c$>RoYu&!3yQ'
    'Trfd-<S@US)~c6<-s#l*D2$oa-p|UC?!0WmksdQ(`(7!%|C^zujjCoHmV1xhiTXe9=z<v~K%{Rf*YNF5D6sGg(SBMOx6>u!HJbhB'
    'H~&_iVD(&fR6UvX5}Gx*u7pFnJ5k_;oxn!Yg>V!wcxQI6&*X-qnB(2as?Q>Q6uUXeU@)@92kY*Y$L!&SqPYx6#im6%Wv$gGy0r~w'
    '*4{}Gtv^dn4J8$c!~7E0m|F8DjS4y$YD8fz0wNl68%f2O*j|AORoVQGTPSxYUK)<9!eBt>YGb4Q8VV$>Ij6_D=~A+c!&td271p!M'
    '(VV~vE1~f~;s%AKL7D5AA=1#`*iD2pt@W)!ZJH%Qak=<W_agil&-_iXJw!I!JB$=3Jx3T$$;uOBQ=y>TnWE)RtVQ8uUT)2?5DlSh'
    '=aH=>vJ4v^wuYTZHKC^ud}rOMK&nL4lKvqCdpW$=l(v*^L7wFMY#DY*y%4h0BJB{#;!fWFBc-oJ+oaOm8s1GwafGQ_y1Bf)o=uRA'
    'BQ)F$4PD(qCzYp-?K6~biiQQs7H`;UjqaQZCS+>EYD-`?uy`BXztllYsk?q5@vX`Mm?EjEoc4N{q_TIF#AfIu=^opsG}EIco5Co7'
    '))Equ$!)Gb5_?OrVv6?LL#O4oMJ+y42E|@vrzoK?D0%}q><Xibv(F^lJv=<l=r@bMxperqPZ!#|+rRF&D3P;p!5Vz^5fQolw|HNU'
    '@<KOGvVUFw7iq4tzRn^y>R3I!DIMb1f89n^n0phqV{3Op*I?_i6>imrGZpOb+>GpW-AOHi+&LZE#Re~o{C_D)8U6!#Ci#SyxP`Er'
    '!({1NZkr^onH@%_TE_00qZZ9)Icv@UtICZbbzy-55#%5m7S^bMMP*V0O6MVuf2*LOs@JBwf(YVzKoXx+6{Kg@?zQ8i5Q|!z5IwY-'
    'W7Dr{W#sTxqo0Z;Ny^zTQzRUr`U>fWH1M(Ny%(Kuf!qiQokEbWl8m9?XTg0?<%c%&{*Ou*J4{d&W8s4={kGiMPWHk5WnsBDk78t;'
    '`l=`mpq?z?xAS^YhFI(J;9@@AK1kvqSKn%UtWKeO-(2AJF9U?%(Y<C@KK5^FPgN62B(?)pZL?_DOQHN;co5hHN2fL@oEF9V8;{+&'
    'o{3+4Mk+hlR3ofW0BFfW<wE9;{RG#A6SH#ALG^Ci)+i5U{~49Sh14tdyTo2)cv6PqS5Tn;3}e)Wpzt2LifP5fdgg(~<*I}98Ow-s'
    'e<!)d*&6Ku12n{|*RRVX(@-55N?TTPna*ZLY749;V34+E;m0mlfOO)yR<IsiDJ)m|_rxd~T%U#d4^?cRmm!*5%eSGkHwxCr0Rg_a'
    'dc3Q_^_RuCgyV4b#S<b`+2d4CkDJiyhAs9Dg_jXNbUO2P=rz?7eMp)1I-IMoLk)YB3MWq;XyX0We}ml}?5@C5iF#1#483AuU4R}('
    'ns@<{>i93OP;iuEtUYr~xgM+&hb<Rda!9nplX@KxyTepbivnr(%3HL`kTf)w4AdO*DhU8bNtAK8%1utF(U74I7&S+!E;kp~iunjL'
    'Ib<xXCmF2yAWDoums(|np%ch^o2VX65#XRuKWV{pUgNKbM|P;ep1}S%y7*E_t<kPhTIpw{*exr^ktK-1h$32OD6*ihu|Kv{+<m2o'
    'MkVjE1H9RwgcU4OknL-<*S_K)MXfER{`DR5VQfj~eheD&{kiIETK3y&-<F7_&|PsRBS8s!zoqaBx+_=iQ?K_#1fVc!HaqGT;<LZ3'
    '2(|0-CJ<V4**_S06}ku&)R2L#i#@S9s+jtnGzYDC;kE;EM6rQbgjP8@5t06S8V(H=^i<xUf54U>ZHYGM8PRX1C)YI>);LqtCG3Zw'
    'EeITnBTn&_x>^FBS34B9(Cw~nq!!&eHs!}xwc8oGOj*CGj(#qE<e?l+W)6a%$(CgXGKRVi@k<86c<S`BXDj$VW^Te`0&3d9iuIsF'
    '9G`NI(tI(TbxE2WT0ZD#x@qx=mSw3B$THxy4f5vLa)idR=q<%PJTIk(6ic5n$gCRdXeC8QPM=TLPu3CU9PAymNLP5+<kq->;RIJR'
    '<W+USIJa%l_UE6U{KL(KS2dqq(FqF7ZSiQrVKI=yhUl169qqoBQm1apyYcMDUa&-p`5U*>{mwcTD+|rdq;2*MITCX0*aSOWET%<~'
    '*au%Xkqv{`u^7e81x>5T9zpCWvseIMEF4Uudc}jzo?JNCQi|<aoeAMaSvd0ivr2>dsWq1<VK3;wh{nm0b%<`5<@0?wf`!<Gj)+}-'
    'xA-(9S2eFMlE{Uft)yCld2)FY9Y-4M`l{-!aB?T}abR7pMZ9}S?%SI8GPWsUvZd5-XTe)G5YOuSKtkTHQ#b0A6k7d0wjh7J|L}8p'
    'lcj5&r1k!8iC0T)b_D?8aQqH9WzAVqu|ZlPpO=x9gr%FryS78x*zOf%kj0Sjg|fD|aEXq-D0He5yXyVthfgH8<g5tM)lG}+c6IAd'
    'Z@Cb5&_H%g3q;GHz7dMp0pi+$Ho46vjZzl)B)i@$MUh2&lPs|mY&hk)5KSVm$^)tZR=;shVS}8CEjIB+A*JF`AX(?YwvKe_@rB#|'
    'S>kVBzJ7kU`*HjE^FJQ_>%Ax-X>WCQUMQ=r^s-hsQO_5l(&JnH71J%rsu~?Nc0-wSf_}u&WcF7&^J0HGP#Sxf($WeL^^SFtX2qFO'
    'kfb=CN5fqxjzd>1FU&^RuQgkiVG^Pz#Zknv^W-`qsN(es7?<_H5XQ_!<!os3lU!6=LXVD8QKW+U6KIFq{TV8#4N7EW!!cG8zzw!<'
    '=>`veoR&3jP^RFFbUJV_X{q{z4H>p@?w^NpgRn_J`6e-Yk`;mi7bKH*Z5A?=HRPd~tbGLFgsqKdBAp44^J}dDL)XC-I@?zOICAmB'
    'D%V^5yJy*ZX&$|RQ=VuIC8kPqfo65u0VbmdUT7wYeSrb=CGyW=)gN^C35Nh%X_F<0!{Mt6SrVRg+_aeG$6!=9vWcBqB%kl&k)lIN'
    'th%uJS`YqI%`;^+Y*_6PzxiJO^ZMiTL~r-@9zK0WgU4rZA(;y{g<kE|h$i#nyaP8K(a(&Y>(S~{Y8led_3U(>@iZXAx=`o2!uS6l'
    'd*`wnS8{ag`FRS%V-3V2St5sOtI!rKH3hYVg7FXf{omrqaKla3MHM^pTd^WHYi2jLiu)2785yxI)n}@D^%5-;N-W1cc(B<tr6U>C'
    'Y1GY<Dir@}7$gy`&JkhyIV(@k0fFWE(%h~p%^qo!{`gnkzI~hcp|il>)UTbP$-Mlvni5+}!K6#6b1!aF3IM2{08B^1zOGNvfksUM'
    '59u$OT-&3t8}O8@G%dcaL)SWd&M?GF)KHK%*&1{%mciFh&n~U;I=HT#UT&%M(a3EQ8~f#8mF?0BxUL&!-Jn+m7@3c?cT|4Wb-!t}'
    'ZZ6=~ij|?SY70YG`OK*^q-cZM0>T<!2G%2m2p7M3AR8VEt8BSM_&}h-YrX8l&vsw$W@VuEQO><mYw3!Vk(6$58qVs>Q42;F>~wqv'
    'l@DL2pv-r2OhogU>p83w@|5i?%h;P`M<aIIMm$jRhv9eSm5oD$LI;I`9TeS6kxoi3B+is42q`$4tSS#GbiZ2LVAwZ4KdbC(GTMOd'
    '>5~Hzx{}N<_@OJ22J)~@m^&a`8clS!21CSsJ)t}d@VLkV*^(P=ErMQdSW@M#o;5T^kN*uyX>@mGt2yKLn(jduS^#W|8cmsGwPn=r'
    'EGxE5_*$OejBcsAjz_E9!E%DomXBpK(aJq!;e#tOZgRK>D*Z?s?T=)SWknIEoIO?a-hCQ%TFt3O%CWi`6dDO=R%C_t$=>Ax@V7cJ'
    'S`)P$5T_~u1g8>=Q1w2}G2T|s^vgj@COLx2emAG_QZD%y-2Fjj5SsP6iung0vZ^5+(>49y*aoh-QG$%+vRDB5J+6c!y-odr&P-t>'
    'iH`dz#B@_n+=+Yk<JEk9LVoGn)93f!p2`?(;a~f_`}Fi1@k56Um+bu<(%q83bISKX#y)K2@$J|h(ZBiO>(dt}AwBl@`K-kfT`w$v'
    'TI1;}0d}UV<|4qN?JVl1JO)iD<yN4jaW2Dc8m@^-U-Fz9siCW1e}u8jP1{pDQW~1|c;;X;5TZXj#`>0kYARzd<TR3v46=Fan7Ang'
    'KdhKCoQSN0ZaGXYEdF&l%B~Ug-rMV&#1!qD>S6PO?BYTi6`Vk!R7#Zq97N`E&RjH>7Z=zlHvr}WqAXXTkGF;TbFH8!tA$M4cl!5q'
    'y|YaVs8Ff_j2?=4{Rmi~Ak0Fec}sFnD2KI9O^cQ6n6Zt_)bz93_3KTmbH1i+rmGX_x5;W1nm%;{U$d6!%~X8CDqQ6Gi9^iRkn7lm'
    '*IvUe2jMhjC;!sm+cl2yv8Y)itnJ{Y7D_MZ+h1w#s(gegyH&U<4`KDH9X8dLU~rwPb%rl$6X{Q6iq?4RJ}0Su%vKwQ85<kck^}T!'
    's6Io^JSMVz6SNR_9`}aH+J&t8jH&IdH~mC+Zj^aq@V>1n?og63+VAetls0(1=PWH7$P?U|8<nJPCHh6tqYH_mchLBJoyz<N3>?iL'
    '>Xq_!rDxFl7gS|HLkz7E$g4&RiAeW-L_i_OKaSUsQy5RTb>k(kIv_JEdZ$|=t!}T><m*+JukuloFFTaZ#7{Q322;1*!M^t{k@C#R'
    'B8(`#<9_PaKMU)?BEkr+yB4Od>5on72lFf=4v0NvkdlmUhr=`}IP9dbDWUW%Ij!E%SVv+JY7O^^5?&ErCmraRy|b%my6|8T7WQwh'
    'Fp4EB7@n)>8%ky+AIM`U3@{511hwN!vaCr1O;%((j3cB;X&UWh&0H=GER`-cc@}$TU1hpHceWWk@n8b7gA(Ven5v9A5?KGD?Mq#i'
    '=ma1fJQRZomBJ%0f(CH-nlGuP>e2f&^Rid-X<fCvvKm8Ct%aUsWwwqLbR|IrukASmKU&Nyz)@(UhY;!J?csCEC(l`*V|q_Thd%VC'
    'iq097ay{1|6?Wj!D6nuNQ)QpBCulUkWxG$hx(wEKz;!)k=F+^L!f{sWym4BlPIPxrD{|GY!aKw1$xwRE(Sx|3+BQ83qqC}AIf59L'
    'l|iv=Q?S}ou|-;-k{^a;KBik6Bv{T_>%}acANofRnZ72{o7?X^Ub|<uz!944^QIbYjvA(WV}4V@IvyqY%6OK!+f<xNM&`B8Zx0U2'
    'l;P}~nq{ypy)O&HI39R2Qc^D;Yp!I|p{r`Nr3R>GX9!DMs`{zrq@qtq9%4K2QnwA4%TgoVyXpgOctA!E-lej7B{mce>ojtm^@uFT'
    'AU8_)q@^U$QJ>cJxqsa3s=Fribb@67Cr+@!wxv(nUcr3xv;OL>2~l8Z7WS`GEJ(pmjyBqnSyxKS6dqNUyXfMJ&O&?y^1)h-l(g;_'
    'HKD@tFb4Q2ZgblSpvrhcK^1r`0F(}D{fcrhM;bG&diY4u+}1z}c-9qxBjuY^w#uytq(#J4kT&4eoGj(UqBWAUE{Udtt3j8~wN3QM'
    '$IwpoUQni##eHzWLdn<lwG8$B&e7$Y%p-<IvbS;8wQSLbc4fR~ENzGInj)<8DVSi<0|knLHgxOa#EW`;XF7MFlL9m%4JUf3B9U(>'
    '%bHH22R-@#gdWj#1zWDo<BK50Srx@o?EBVJv}#&v{V{Ehl=l+bj?%Tw7WnDCt>?^I*oaXbPQ2xthV+Mj>Rkx^*;5I&u}CJqq0428'
    'V}(kLk3s0x8Z$LpySSxfVIaU9RJ1;a4zwbJYbdg&401or;S+9UjkSmo&&9;X>k^^L<=F+5=AFN%U8?apn@K6&;5L%iQ#@hQmk$3~'
    '14Fs#Rq7sj!X;8{T5h8<pFu3$Am*Ew<sGhs=QCFo$qtp8W{N1j6|S0B4)b(mesT`zz`D*)B9?GHQ?MIYcR6=NEeVHxJsi;*4dc)m'
    'vcr;_LbMWW6tYWmjd?3MNZL^lddC^CG7hI~fynYvA@;5>aLS^>zF;C|(UN6>iwYG`VL99Rjl=9i)EPb7%3BXI-QZC}@{R?R9T}u9'
    's=;J(xw~(HHz}*^8`RG{6fr+Tv&d=Hc^TZ?mX~u4h_MD3z5#sg1fD4MM)|!B6`v4eG<%`fC#&k%HQhsEhD|_P%*f7m$OP&qlJG42'
    '8p|NMK{(Sx@qFgP$6q@gQ!^-@!NbCcia@r#Yw}pM^zG2073NZGJ^NmEC8>d7u&HEUu2Tr_$f%9eZmu>joskT!xcw}BxLmhxJ%<Cb'
    'zSDkAa;@jLE)P?(z)1FCEgfGvd*)+>E*baritw=`Nix~D%%V9{<aqNWN~PJhZ2YqN+}cw{oOJOb$c1x<ZHpYMwK_ntJ>+D-Q!WR8'
    'ER<&z2jaGcDU2uV`b~wFE9z2scwoCWn*s7HB^(&5`*s#VX9==gXhqA<bK$>hBETxy&TUzvW2}A~Z#1t0aHV_>UA0{JVW%_4V+R+t'
    '9=G+zKn~((Le!+4-}QjGtt&4p;b2jP5s2H3vKY06pM(4ABegm_UdqRW7g+o)t#B80yGxI=4(x6RQ6`o=UB{5sSyDxWVZ*;=KyG<J'
    '$8b9cw(T>}bQN4}snV<vhl=y{9kfcJeeDEZ-K@n^y}>7I^-dOhbp)@TC@Qw3f{BgMdkf?2b#so~#@eO+_Easp_w4YpfIAIUM2VZG'
    'E!_1LMD;i&AItg7iR`g0M986P=fMa$U?&Uqy;Wk>S!W)QhujB9EN#aX;(Rxg0E65X>u8B4x3~#fR8S};<Xn(LjkiEbRkRV%stpw+'
    '6Vzi3%+X=E6<Udr{Cmsj2W*KA*J|OT=Y4gt76qdUeM?H%R%Y2SKF#$kp@MPZ9^Ur0Y|YL<YAnf(l&Dm54b5;NvIx45!KW9x`;)Kl'
    'M}s#SaJSV}9U5?I7DxfVT7F<vicR}4gL`trB}bZSq2`L>GUsBvR_ffoobv;Z#pRoo(ElMyQ+;VU*o7o@^dq+fqW`X38DfFt!)@(K'
    '(Vc=UeNCZ7rD9EN+~J%v1GW%3UyVO+o9Mhj!gEqy>p6(~W!B-9iz@21P_$6AgJS2H3QR#Crj5%1hG>n#D+&f@U1p%w<zSz9?_CGq'
    'D-Tb!zfqq+X^fNseOSo+D-SNA|4lj6*Wj2*;t(b5^#)=GprWb8HOwvrH$_vrf%Uh1?&K!xpo;%K8P?02-<zrN$FVF`06S-qr*K*g'
    'C46*1>C|a;IOqt6Qy2=Qf}pM67nFX-NEw(q9603f9c7@OjhWlnb@0Et7U;j!*~MXtURzOGT!7Vl;gVRcIn{WeF0>C1#szWcn&Apb'
    'b9=2Pl8hYviS}{XHG)!*jXV&!ep_Ffm&tlW)&i8+#wMVAiQ}#drjk1H7^HP#Cmy9TfE*<Yizk=(&;FEGVmuT*3m4Css83i~;H=Vu'
    'q-Fc@@H@Wzitw?BYvopaW{(At(1RJNJ97wTe=EeGvyR?a8J0uWta(V(jc0!9T~nv{X>7|({d4rRSYb7F^WZ=1=&C{!`P0-MrTxKa'
    '3UYU<-$ea^(z2EgXOH59d>n@2JQXd~y3!U+FySvu!luy@IH;zb!palfqQl(uP?K*1cQR53r;Juz7OFaWwMPXzHMVmZupV#mNX5~i'
    'PSBYR*I%WJsowU=71V5hs9sXSKzF!WpV2FWJ44JriL~E})PhP0pVVKYoLDb-VRn86dh+_VbQx6=&X0VTXmGU>@7Bm4QAyXWq+90t'
    '0}dnH*c*>t6?PvZL0)QVc~1`@rQwut21_<@?8of>My>gc$srb!`3AzKs#LVQ4hO2<wmdVnU`R!IhVagX-knXJgcUTDV$jhYqbv^@'
    'Ac^#7djjrEeiN)^^ufW7Dn_Ahw=A}2f(Vputa7YuRXSX<3+ocOTFsWJ)P$!$4^6-XFpDpqLniD|ar7uVD@X>j4+<1l;oeNbv<;0@'
    'wT))AWKN;2igY)vByX0TSsng-*+gwLe5HFix`+$0MOmc1TlH?ZztMX;Q)l|=Jat%7v66@dMdFY2`}Jv(GiO@c@Xv>=J%sREC5cdX'
    'iX~+*E+x^MqTbnkd>s{(fh|0+u0`tB+9@Z!cPcr~ZXp|Vqn&ZiscdeyA_)Z_l(bHE6kbM=7x5_;uCXFN7CX0Qb!DQP(7uQBF`(u('
    'SwQC!uUe5Ap1Y0&rU4LumYFknRHSBS!iuSOFw0gk4#;v{b_G2v!g@6~Z|8KLHQ3hg4TEK29zZ*p3UYfw3ULm?WQyBsa4GKVpNvcB'
    'CJQ&6B-!T173`WH+4`5=g+ffRProv@a!qX<oftwyRkRaoBM=MtwRedneP*F-R=!S_l7mMu0Wac}UQ{T|%K(FGX_TEj{OZn^ZNtw1'
    'uOu1EX!OnLHN7eC6wERtMXAbei{T5xBo=aV)|iIvO|mi5iowjjfg+Lc5_r*(>g&r14c!E4O{swyp$=!)J{XZ*wRZqooS@(xwAEMT'
    'q!ORgl;b+wbOLnNhn`z?<_AVww)Chmyn$}&Lm1{{W^op}fI)G#<gy&`>pFU^J&QVNS~Y-abVm*}7|Jx`G%jgy5X#+F$>I@)il#Zu'
    'Fg}j#$xLyaO|fMLzQY_fCVNg1wk>%j5h1n!gdEEe2H9j>;DO4PsyY5diI*1JgfwC1YcjHf%j{u`IAo)_>O=yjym#ce^5V}iS4NW~'
    'OewiGEQ4>9q!9{7%k17+C`v8KX#q0BN)F`=?<ZOm(jLPsM}l1{>4)gz=XW_DJC{Zd9;T1oxD*8-%!m@`*#}fA07!EFyD?bCi?4Zl'
    '?Yy(L_{lO+iE%@7b*XXunrdK2LlZq?dE6b)4*nE#qjs1OlUI2~Pqo2dRRS3~>gL~bHRi3qo1a@EVmW5lk*z>w1U)+L8Z}?fR0r<}'
    'UhU(&Q!lmiL5;^V%6?~`bgDV8UUlKfr}*$Nd0$EnueGOLD}!7p+zNA;S}?-zo4}O1xi>c<d%xk(+N~U39rJe-Kwtr%pfvPN1zX@1'
    'gz~;#cgVo`wOq#AQ1uSe=NSsFUHl+ZAuv@Mbtvz#gqO8A?w;opI_@me;B4xycU;a*ZF-7yoL~2?Q=G%Bvfkg1nBO3D_Z$qwf{2KH'
    'a+Fryy)!z6A(gPYTEZgirQ<^KMF)nDa{8w(Bsb-S7u)PNoD#`>ZXiU;iJ-_%3Di>#o{ynN=TMUY(z_f9-^#IqE=9-=8tlj0f&JKX'
    'A54{I1&*>xK6)`_!{aS&QyV?bfR8=+4#4)^#^A|ON3iKpS|W%EK)oQoeJ8q&wF!*!Za=eZdNW&>#_?6qQ7uh!K=U`~%B%?7^2wK}'
    'X<JoflHzbMEvHI_wWj$8493d+(o1%KG*8QUI#nm}sqDQP;JcMxQU>yLtk_*LTDeGEzu6QYC~Hi9r&>slHFq+Ts$Oo8YiJ0NNCEvG'
    'jzW`iuUoN{8xZ1@rwr5lM5r=qIN|!-9af&I>&`gx!+_4df$k^dTx%M--A{eKIlW9zOy>QoG^xQAV=y}!mVKL~d-25jzwy<=i>fbO'
    'K3H+H&hv&RsHj&O=(3z6@)PX+S4g>^faIU*0Gy}Aw&CY0|Ea<0dZT=v!#z?+t$QGHTt?mJPy^xg3qAM0t2GFY17Mr@l`j0oSo5w{'
    'tz%OPtta(LHnsVw(h<=-12%{OkU>V{QiacnoTYLgJgF8W>V+Env5=br2?ESP1tH)_NPI;cL2xvXF1sG8td=MuiyVW-uX%1{F`Vp0'
    '(|wsPTgFya^i!xfW3nF!?QJLEH;L97{e%nlzj$OkdmsF6)!MQy(4TKaMp(3oE%MZO@e(dJXG`$LYT4*$Qx2U$<?kc>-imgjk@`3{'
    't%B=ghuGx4-bZsF@_9xRXaClr>_%Nw$R-h7X)CQ(?4<bBnFgAas6sV$hckkPtBIQRX6o_K`zKW}cr7Vb_b>E9a{IQi&79xP(W)X}'
    '?!s<3^16FX4q~~w8wEVUSiKcoHbGZ9TjvCgFlUjSW>b=l_#ozIq9i4YKpc7**^DSAC>QN74jpHUf&%IbOv8&8w2Pm?q&+UT7DP(t'
    '_V$9rApXuDzCL}?Z22(n-@uA*?*XXr^+|0B=(>eRh8{Xef9&NsL-h<a8=;7wxgq3!?zsD*$&NKDEF`)N9i`_xJ+bxbnEMy$ww+1;'
    'kB^M)@ndEYpXz|U9TOc&?MOOUoTXslcRMLdR9M@*2&RDqockR<yf1quZ#ACDXSTNhMD9wu9J#7UO8_;K+f|dBwhiy;zD2(;!wx@}'
    'OA(=r4U|V2e&psAEZWedJT^|RSCU1gbQ~_v+wLu#?DUTe2C^Z9l9@o792<ObceNfav=*DYSSbAR{o|((fBfSq(%B|MkPQfh(^+an'
    'P@flsI0Q3Qjm1HzP0x;s&ka&Aj+~ZL0qj>)ZVQbx`C=Fmne@b0n)NFTcnqFDiee{Q_QFQ2Y=Sp*r2Vu0c;%Dc$hKWgzf5(ttdv6c'
    'K{N-ci>DJUuG`MsB@aOyg;k+ecsAGAMMUryk_U%*?qN-PAq&qzWo?g@Cw{*8VR<PemYy$HI$nH3?xv_yv^|>K$HbvQe{-0Av8y-G'
    'MXQ(GCafuIl30pU>H<Shid39>T)f$kp&7fG;{dxAsEhMUv1bGXrIff$8!;W9a1dFXg8A-6<6zBA7-?_jN_$3@Isy_Cq$lZhN3phW'
    'U@dm)Pc#NQnLT_AUO|lJ0A+@3rRB-jki5{>_Nod3sbmRU5yZ7<jtYm|2k0E7+Gf+WNI<?N+cr26*dwePw2$wwPOkGm+6dZZ)72(y'
    '1%T_19WISS=cv%zM~i24O$dff{USMS3wBpe{os|-FIO#h*j5q>VDzeU&sV!98yELy>ERE+0(pGgmY)*f@;NAd13KH1SH<oger4+N'
    'pCx@`E9vK3KP}+FCXd_8RN5<5d+4ef0T)()aW^yKC3Teu(RmA`6GY+YrgRCEnBN{w=Sb>%IsV(CGV35)?+x1VIcSxzV7Y0!Js4(@'
    'o#&)ztj43Oi9&DR;b3Py$yBe-%5XDDk?rTV8$_ovijWXfU}+%Wz8-1Y+V@hT_boL?g9}d!+mWq3<?c(yLc*bw4JT*AR9bmsGZYfG'
    '?WM)OUbGLz;{p-WE1H6~#>-d$3+RK!hDM5%(*VBeAaL=i(69w5+!R}IO0T?RbwCV^R_@wjH9ge`84X>hg!?j=6T~9np*lnj+MMK7'
    'Xvq_+Wnx#^^4{g~q*M!g5fCyzxE)F5&p#l%PE1OG^gdH>Qy6}NgVjeIQV(P6z6Ly@St;$7|A{*6zHJ@m(1=I%InmxE*}<%6E^(Ou'
    '9HRN#)93f!o`_pIQ)50pWB^N_cb}eq(}Pyaos*8W7En}sYX+0U%OaEw#7*g;t8&bfb<&gMxhk6+uF2|}to~Mn9ot_s)iqOHGu2F)'
    'Dho6~$C)rwPA^NAU5)khLO!L{$%|f7+BKz>v42v_sX`oR<{Xt`=wCD0HIrR4+1~>05zl@;oagG7cd(&-oWXJ*nG=IENTy`2Qn)X<'
    '^WgQkTb)sxXTprDWLL?Tkj`~B)#ZNZ)nvMcHQ$9#_HwQKzdwKZ|AyC0{4Ji9k~r}SZkacE`Dc<hg}3tI?lAh`mytJf%l!Q3RlNW0'
    '<LCE>i~MQ75NC7lmwx}}ZubRa+~hhFUq1fhU*EqRKVhvaL3C<!@n#ucy~98A=a&-cFgV`iFW*0Y`tZk(zx?gHz-IpF{k@Q848Ol~'
    'H`ys7PqfDPfXq#NFWy@pzmd3%W)B@5!z((K`(C7_ObPp+o$2@g2>f0+J&x>4Cs(oOgZx+#zkNIPtjd3R;=3Ix)ylrx4cQ;eZGr=D'
    '&fxf};5w!p-B{Zl5;~J89ehEYGbjUvpz`6Lp3P0ME2MVkCb=Yk8>3?SMS1_l)4hDQ&Izo@km>YCIMHq?S4d~o`j4YLs<2-|_AU7g'
    'I~hw?osn|iN|ups{TWHVd!T-bmv44Oi3{B<<cTY;+UNTYshQ?AbHP<^Zn7-SQ`NOF(^F2xGn!V=p5HZx{O-^9haXG!6*}aQ;5+G&'
    'Ll$&M*Ox<bFW2{q<_GvFXPfbC(#fPK>0+p)y8EVrkr~b#{GYa&MFhXsL36Y4sZw43*zLyXBa(+YYql4D#GvTY&s_Z+_>mlvDf1XV'
    'x4_odkDw&f0_5IEFD@nN#Ofgt2mdIzlboLqEMz!N-TH=`o?!ijcr)Y-UlEA9H<n!3-H$3srT14D00ZUiY(bHdR(^#c5j+M=*1gD7'
    'm$MWq!ngJw-bg3vWX+b}UUSz`;mvpbRM$^+?d4bX-~aj#cN#inx-nztH!dy+QcYq9`%1FKrkcqH9KN9W$PTW72Dag~Dq8tT{+{9C'
    '75k7dohX%K+b0v2_@wyqWf`Eo-(7C(yp}ld7ZfxlVT~D}=M38s27PSV*+AeO$bH~cVNOAvVynQ7{ydZRU2Pd(WvMGl+N(f0i*X>U'
    'DQJF%?Fe<E$_J6UWFKyo-Gwkr5y`C>8cI%&IBG>clh^SabbD<{(zXXmFIVIU<<q08IENdMCPNC>1{n&9@shAKyAGjd9#!2oXN_2='
    'P)hx_7MB^tr3{XgcoTj=2e+r7RP*;;dUSqeZ!F2StG8G5_0ffi4n15syX~pmL<UiCrDZ+z*4ijc@(patE2I6}$R@3n)h}vulWC=J'
    'Dl>xlNwtN;N|#W)4oiNQbkCHsvBAr<d8vDEg*CYjr;P>exK}V8V<WX>&+CB+u+$WiR&s;41QXbOBgxwtUL$^l8XR2SDh8L+0}@!w'
    'W%ZJ9B8PIU$TAnZ%S@M=t|@8&+k94}92N)Pkk$xH@zTmN;#t>U%EZCsSJ_}Rf)21PFMFn0xYQBMGef^$^9;RYb5?2su9ffUm``43'
    'wJoQxv1;DLQ}Qr>QyE1n64-qTo01t_CErU5*67aoL?1p!WAe?eP})_$v8uWE7t1i|DV1bc`WiqT`H@sglCIAfiya2=N~BgzJ|WsI'
    'mS%Yg)P`pglsN)zCCh{B%`4cK;>mPGCtI;wm9%hD#b##zKpjSB(N7ji4WRE+L*%o|Y~v4a4W?$ANXEz#N(hk8K1-GozRnL{pT4x7'
    '5{0l&_iLh|mS{0d?oBY`hY?nRoyVai?<bcb&pKS3nU++E#xH%{guuz+gKspZYq8UNZt&J_Se84xg`S;?-ONdGrEK@vv}9xVOD@Z<'
    'Fa@FCV`Xzxm@ZhtQ`7l!>}W_Xh(_vCt?}s#*1+>WO%K<J%}#WRINj3!{oB{~`(Jinzy2GmNs>q?-J6>(*id$iLRqzk<!fH6;91mr'
    '@I9%ph;`DWf+RhA7Y*dGgZLu}T<A;=Z#uQ=6`y5q)Gx7}-Y+KOTcNt2!M&sVOiQdg)1In7S_Ak_t<N|8wM+A7NcEkDMrkdgC9yc2'
    '^>u$m{!1s;)#>TZr_D=EBMklg0h@c9?(HJO(&Zs=u%*yqZ}}Hq8)mUavE*?&l&-PIS912=6ihsR+SoJ}&f&67Ip1sMbt^8*$q5R&'
    'c*sAgkN4a;`GgG1)6>gsZ(I95gC%cfGLj=k5b&16cY5<yg5Mek9&SQE_T#J;i2105+a~`2T_A129F~b$-2^ap)0Ea#b^Se6{G_GA'
    'P-Ve-CP3U9ip*?9!~0*pfBf{}j~_4M+jo$VN51~p>~!IC{G2g(;gfXj*9G|+gJj8avr2@#Eq8@Xeb%Hfo7DDt=*Jc=!*iGS1S_Pz'
    'F?!nT;Cz%78C33@F{$Pf3|%Tn(6&{u>q9R4!NJ(U9qU$q`G-ZtjT~xWsXHrL>dQajL71KhQdQxsJAAWyLh8I-hTR&}JQ?C^3Gu)%'
    'uAsS(Sfc0?cQzKTWwjPv$!AtLUJJKKN9D_+GeyVPGfDFnOPV)LHr&A^Dff|67t~SUKqc-qwcy$JNpopz=687-`eV;i4SM!rt)?1Q'
    'xtksdJK4tcWM+qSur)Iq+aI~}j}}5an(L)7=%zjFGvY2+2(<+q?J&{kk7_1A>p6hW@BiHGzIc^b#qePMpXvile{(ApC^A5OrISsc'
    'bW&S*E~#W>bVw-^4+lWcL+?0vl~6rJ@byytb=^B21T$5ET?cOy|K2zP^^Ngl+6)YRs)YG(vDws?-sC-}INXxX-(yQw*@)C6nUoHW'
    'J6dj=od0s*>);B_yPyQ~PR;ft?bfcypd}Bu<m)R3xX4DGKVrabSXgP-NNV7{`NjyJ(&+Un$0Y-OxZsW;#Tu~#|5?C?ldpb5iXU9p'
    'C0?a-WrPluT0<47oD2sX>dD$&SyOeS?e)&n4L}mH!X91XH5!d|rqW&Nccqt~b<dU7js17)*cT&=zTXsJ?s1X+$>5LVDy?VN=kbiV'
    '`^8kabB6}K@&Q&vxvyW4q$o{pS-rNT%kH!>tbuIT9>A3Q%y*}Ba4m5juzi!O8n*nZGQs4Sp7A}Ti+o$$VQg{Pnk<n>2&sdS?P@*h'
    '7cvPJWzX%cd%^>#ug@Pp{p;EPzuA=FRTKZl(S{*=2crbp<9vGX>7IQ&L^*g{PAZb>2ER!oTW;RI6_5!3`VV)-a7zoox&YJZvL`pX'
    'JmsL2d4G}2nw<z9<BgaiVYd|j&Y{dXc?MC4Mx{u4j&iwgE1&*&*0oIV0~v}|5P^e!B$Mh<T?Cb&Eu?geSnkoj`Wf&#h{Ll-0Q#n9'
    'EmDKwK@(Nlf)?e~t;}590P#bspH2a4%2KbOEb>cm4c%FijO|ld2;MNMB43Y=A<aT(S^BApBKA5_uZXtM;8Vm-ZSQE?0v1DL^R@8k'
    ')41dt-^m-X?8va84+~yKDT|Wy!$J(ZKpq&0>aR!`CaGPWM5^xFZVNhhWd-UocZ46m`98~()vZd!xI|cg<K5-a6ZGVZ-3O}9ZM<=V'
    '+1q*7y`5;&6T$K`8M+aO)RjEZG+6GWSi0LQp<{ZT{}>D7u2x<LVwj*U*%EollqO^|eh`XYLz~6mhmPfWP!6r@2p}iBO-eil1(QjO'
    'VlYI)okfW)=3zZ}0LQ<pXdbYiIU`N7>k7uKkP^KkX)L$p<x2^@!gAT(fKKY;LF1qvpk)MlsyvSJ#5xWjW;_Wd!(R60DxrT58u-Dg'
    'hupKsgW$pK&*k#N<|d^ZkAc563FRXP*Vi$w;ZG$O^+w$r6(^unZQ?izpj{P*7~?FAO}{l?-@RQbnX<~=J&G(y>=-mA4L-e=+2GuY'
    '4h6HhD(G5YYKje7C7_VO<2AM-2qs!`1`{3nb$U4ZAX4vL$r@4F^j&$=qH(iTg31-vrD%Q^io+Y$yT<*ytVlJC5OAtQJ5H^7H!pLt'
    'MhBm<RFkj%$nJAGl-;M8mZ7&dFr&~zx}~eCs3g_Yff#=HRue#Ii%Qp`ub+}h%FUdLKFBR#*KP;<C-w>Yn@O?nJRV#3rSuTCjIAm+'
    '?yGH4`cktd`kPlTjw``KRGpV!#Wv=Ie{yjWo<10+`7~>187W5zH&e&n3N9nj#&~9vA0e*6pzCK*nXQ#uk)@XhJKWe+X2Qdn9H7l7'
    'F&Ta^6KaaTzwm_y8fBlj5YL0gUO6fSM#6~eCjBdk3<s17y)}bv352aHKu#&)b?8?NCnz?=gdpb=UH{L!Pfx!sG|x+=J;F8cXZJcj'
    'em(s8t;mp``3PvJ#~mk#TZeuo__`ru<XBE$Fjve+{bodnDo4VDJ{eoe)kZDZnIyYanT?<%Oj%FY7+Za@+*8&135XI65=Kk6mHG)+'
    'EdQd^!ID+7UE?Cjwj~Ex&!9ROtNK#Y@y=M8gDYxj_F2nP>d8ez=RpH&l3g*seE<0A!yjLMRQ=yUN|W%o9aK11=@mv|b7M&IvFQBo'
    '*Z#-T(-+VIrSJ@sc4Y~!Ews`}HIo8)p<UBQnNQJvuG%<dfH+QaO2`RHs{#AM&B_ov76^d5PMyL7>bNug@zcMa{r~?pRz}))!9!0h'
    'Fc(HUs`u<rY0`zUK&18{dcuu4d6;LI59EfCUlr=znReZF_nXh<ho0#-6PGCDFxYb;xB0k#Xga8K6EyV-Urz{<Li(fuVUuK;$y=na'
    '=D}4~UUBx&cr~3`wm?!>`69z_-Zj}(sdIqT&vbb1@t|WemBS0-QuvqgKXa317X-k4@^E;@LVeR@B%NZ})k4gye9RhR?u5%G9O<!%'
    '@sHx`gTqLU<UO3IAfLSx^*`@OTSj410~i&B3b>FEVqpZvj%%m{Z=;AOyh1XYe~o&c!<!0(FGj&As9xW!!KECrZAF0>?5mBX3oV0a'
    '<j(B6sy@Gkqbb~0R(%#Jkm%a3dC|`$!D#VyVj+>(T)%G_kc!R5a`y98pHk74z9oV(@EV;ON-7eEz;v!|SXn$e1i&3NqOca(HCCX;'
    '5DNARRH%DK5M(P-5ndXOtU{@SYKii$$9+w3PLI>vrBo7!_hnfs966yR1Ch)Ljcw&fZ>2&vtTja%YcS9PC8~=T^_}yXPaQw%UW6a!'
    'nZGHvhsb7o2iIxRb3|K@a6{`+ms)dYidAvnb@Z~DV<8$s+0G+dNeH~F)fR#1M5+lBeBe9lP6cdBW<P=Xxe)B-u!a)G26}*3-scQ1'
    'y-8gTveY7N?8xFy-u@%iszuvmuB?~#uq&hurfTWt^7eW*L5o*PEZhtYUEM(^m8XsEGnB&0Dgcp$@rJF|=*}q!mE4BamJ@9t1~<5W'
    'sbS!~a1L}O@vX{qmLjRCoa|Kkvd+6oVl#9e<2QGPc6Gg*0SchCgoI>ro9mCn-cqcXqV3wyX}N7ti_ern{TSIPN~r3I-arn!!U*jg'
    'G70xjPtP;@-QsU99sV8Cg%0laulp@Z<SbmU248)=XCJ-AhjNq`x^a^I>-xV)bCvaV7P(Q!>gi4C5WoKGHmbtho46fYOMX{LZI)fO'
    '!mZkHriz<+?<OQWjab&=Y7ykl=};av*iPjCr6gte59FET6JFvL!fp<erE9tMkjYQAjNLUyEt=1A)|>%Wl^a9q!U6>%$U!tLtWg1r'
    '%A^LA&O;vmRzX8muT6Ia5ybU?BtEGsNYAX@YsW_+7PUAbdT2GrreD>{$l<F-KNU-ol(S!^NH{|E71GOS;A4SMM=hDxh*U+V5ag>Q'
    'V+i$^k_g)*4{hfCAC)e4IG8HN!be&9vD}wV_QCySVY%IpVq~29s;r50Ia$E(5caA(w$^3q#eBL$ki=20zSsCzokRD&yTa>V2ME8T'
    'd(FOl?BCR$swR|3YzL~^X3?;hLixS$Ag~LLPHj*)EsFOy9=mfr6TkS3RCchbMp&Z&(2|GBh0GoM39bt#X62xR>iw>*Q69?vGb)7('
    'saNcGiM`73qzuKcpg{i_#;6TJ;XQN}(~61p%ma<fRR`%amJ#RvPI8U2HQECPXoxp&-<C(Fp*k{@wyfkboz0BY7FbQdAZ^XUk6o?+'
    '>BMuZU_H1}Sg!Q%iBUATJ`439s@OiSLo~UTZ$oEq6s(T}0(^1xd{=|(FN<*r$KmXYCq$~U=c%3^H=)%HTkIPOFC%>DeCF-YYpN&u'
    'kTUIcI9FeX8ulm^PM$i@#QUxP2D>}hU4f?(^`O)ldd0%J06mU0@d6~(@n2t|;3&sfd*+yOJy<6WTQ0WbkZ6Y|^*SJShpD0#1=8%5'
    'w`i3iX=p4Ns5#_S5&({pDC2OIo19RiAwwN8YEDvJ?yjyC^ATop$XHlUGFbCLlo*39waN%XCy@7;s2<J{;Gj@HYr%6_<FANEcC5jk'
    '!2US8_)<x&(XLWj>1U<bEi1>7C5XX@B3fuDvY>CVKekldeWiy+CGWBWyxE|H6)aMa?Q68xzTzN7tu3Yg^&RqIY)R*S3>xzNx$0|L'
    '_Pc7|mWZX$wm6fKpoD|pQg{Vz%a!}o>pc+xC`_8oj=F{T(_dDE+HH9g2(7v7AB?;TU4#m1$iUXcp4c2!O#M!pgI2t9+W|SE*gz~o'
    'tDKyONPj&IhlUDzDsRv~V9SrTL>u&s=r_}o>zWH|oGI!O_CwGX1P;X!r+7<UEdkG~9g17%c2_r2i*6m8^5d)8?F?O}tY1|}KbJo8'
    'P!1<E2f@!|%Q6EQLtTgXB?DnRb$Z#e6?`8vH{me>HSJ)<de9+`PdP_vz8KEBBux%2A9OU`wD?5JvQ!9U8SvT$d2?(zLStF<mf{|s'
    'm(oLurB4}TRt<KvlA<H0&!_7r>j-lW_6}O4D?Ds+Yuvzaf~y(ws=8pD+qP);>#r~V!`+ovHJ@G484ApO@o2(fF_6QC=$KO-?Y@>$'
    'r|!zT@$AQ5utbXa8~4-w&N>z=3(d`>ZT1a05_0U=1Up?UrbUt12VXal4TIRR7{$#6O{>WsLF_5BSO8xv98IHo#e>eCTsYWLitSmQ'
    '3E@UrIP(0nN`v~THJ2!1FX+IC#>tU&h;EqW^L;phh1i6Sh+TcR_%tL}HLov{$c3G)q*{V`a(NORM;h$<s_Lz9awqd~U|p_7yn9LR'
    '+nM(=wkct<rPOa{!CN*E&+7X?Lf)@aH|m@eTKzt@Ab))L_-lESrE8s}_5N;&S4(Yn1pwi2{0=x}%~?{hL0Tc7mywl(rJKaNwnN(3'
    '?iFN^#gOoYvbMNziH^P~bgC1(>ciKkFC@3*q6pE=U5o5?bMH@Yxe#{HK=w@wM9ZMQ5sKIW;@X2Yxy>exQWp3myWT8CkwtrxEU^@9'
    'IOVwzO(L+$1F8U4zj01sgPe*jHt|LwrQ%T_S?9pEj&$nrh1=m-;_ttI`}%(W%kJyfe?R-L52Apiz17)yp{%yj%Ua<?Jzs=Mk8k-`'
    'Ot&PfYIM}t4Q0*=`Vl9S*<b0*i~Z?9Y3yN2ODjOsJJv~>6&FfDlHzz74R@tD4qdgpFdJdN)@)gZNr;{lM-j^|lk0?_inl9ZT-F0a'
    '7&8}@v!TgPa#3vwJvvH7kqYWhpdD`aXQ-eyD3Os3$5=@KH`u<V8$9@NTGqTlnSwLY>A=CHrRozlWZ1&Fe;&#W!X^Rbo5bu%RtO4Q'
    'kWAXOS;$b<kcVQj_7Q*+b~c`gbS6N~ueAaUT?bd_Y+nK3$i)w<TyOF3o@MW)dGrEKd7?Fxm@3T$n$>9sn2a8Hp_wT51qRTU$Ulo!'
    'f6(1090F{mO_m@Ihp#GRNqE+A*J73*gHhedCU$C(e7=uIiVi8U>cZ-4J@`{K&y>}$VYNs6=6n6m>(A2@z1`b;`1BbK9-qO5WG>hg'
    'dbKwrn#|Ah4%~D^KQnr+N2^b%Wk^HUv-5ez(|`=?LS5zxKUANo>eWlMOenD&_u#>1)0B>6P^VEhOR7-(t6`8tv^qzG>F2CGJqHAq'
    '>q~RHsx*6~P5R?sdHeQl;)l)xe^bA9h9>j!*J?^^Ed`S<rOv&$O(_7NdIB&V3H!P}MF$!+1w5p`XmV|j!fwD*veLBpx(;3I@HxW}'
    'FHu85+GK0cxmX5YLp{5+#_Qm^c6zy`(nlk=No?$wgH^UmE8x0rn013*6<}mO*4|P1RoDHd(Ym>STPs$EzN#$@UF9>U&XA%FY6}Q!'
    'd>L4e6e3*w=7DT@D6F#O65#`Z3a|CD4?o*|y_=PR+DAF}O0A_UQbtm`!D%?FGe<2LU9i*f8B{)ep@K5s$uSYlXRhb4PRLWXvn*q8'
    'mK}}QZ5#1G$sdN_l~*<n5egj?26j+%GetTnxsW(ho*<;)XtJt2sL=gtZG&Oo`24K0ugPcwx~ESLNa#v3zu<?iL>kD$I$`dBaA`Er'
    '-5LxL_w|JGFu>y?3uH@fw6zF&xnW6_yL#5p7(M<sD5cTem96HC+iSW9VQ2xcEowAnlGT<`zq72^GU01^f-}0M>N*~+atF%^LR&tT'
    '%|t8rkcAJf$hgVj9;oyqZL~j<J(d+koO1S5(R=r4)M+)R8Y#!>W>9D(pjnX>+9!LL3&7v%z-Ud>c0in}1Q47`FhbS)ILCNfJ<~4-'
    'Et%v9D*N4>#!I>6UvT#anL%jQ>ni3Se8{SXbWGRue`6cC=0*uJmdj!R<oCD|j`TM52Rbu_kt90qrx4RkJ#i=Q*^gKA^$Gc<Z%?1!'
    'e|supu!Vo^^X}8rZ^REBGF-Cvb4Yhf{>~}i0~!0UmB+VZcSQf@hp$gxoP_k)-{-RyOLV=k0BVh=uLRhcu9}Mgi?*|<oAMYmp_E&J'
    'md3dZw`sU0Dt*awYNUp)e*F=~GB<5c?MP{8*5jFj%|M9$>=^4?0;;Kuy^zyLHZsWOtz+V*6#TGa%5WmG4!Y$qxv==x<tV#G(0gyM'
    'ZxU0qZ>opQ3$lv~X;g3mg;FV10&ozS$2oJ+SYBLUquc<P3y88@g+AUE>d&=;o~#x!ZQtqN)Ai0aEuccF1~7Uk=Jg|Bfr2m#jpi-M'
    'J)s=dIyEg;vSY?JGE>vfYS*tft<L$HwwbO@q~9j1RcQLu4Sda7rZ-dZ39E3C=O+#^TSKm67hZb}yBvhml%4!bgKyV3#>b*&jj*<Z'
    'n_4Knpl^Sry{qyOrtDVXsyu|%t9IB_TY|xLs@564s7<6lkttf^t^1s$`Y~H=7-np2SW6Djd!hOaIrEsv_D#@2+<Dv^CTkb6>NBRc'
    'x8C#<-MLZbiNX7}rno~%#%RC0OH<n5^`5h|Y#>i?XKqxIx|Qe`MUO5dirzuv^K~loA24t<f2dc=*Oi_@?_W@r0Sz&<Mj)>mEhHk{'
    '_Ynbw9RE08Lr!5l-PVnlyy}3=tmvI?iL|=CQj@P&UB1dkO}^|<Iuk$H;2KQbdI$U7yF|(}CyOwm^p5+fTmLMq1B(bFxb9k*x~4xi'
    'sUOU<j5r|nltD@|x*ZPFq~NfV!ls1Mv*fgTLt`C@MW{90CrWrlc%5{hWA@IjqUpkeMOfIsxxy%xtYCPqqHidfm3$zNp)kNKJP_25'
    'FUhhd4K!Ji?J$mzCZ%b#lQna>G_X{<*yLI4opqJz`rO%O@Wg`&$PP-Jt757$>PTSyi?%OyRiYDsaPUwJCR7TKya*b=;cLF6ma0eZ'
    ')6C0W&8KzM^2%xqMYR@sl9kyyR?w9M6}-0R5d3H{uK-7(jUGazo41G0DW5!NeU9lp6&?D}n<_eIP|EdOgH+goN29>PjZBq&%ATOn'
    '{Fd!L>FP3A+X2`0l$lHOdJ4x`sq@BZnL5$kL9NJDy9)0Nrzb<{IY$rTerntFD2&dkcI60SSXKtbvQ5EiPsJ8#fl7WDmid@&ZIEC&'
    'XRQ~rbbja`J!JZtNN;Yx^LXu^*#bvsvd^1pv^i>+?v43P3F~;2<SXM@=5AAQDjAvAKEFLUC{u>BZ)%pow)DO%4C8p<%}7bTe5|>W'
    'O^2?k(UuyZnw=pmZK>*~mXnG;A$f@Hz)RgWTrNwEbnmJUxZwdAJ$RSO>Xq0~IIPpib=D)Y9E02_-IJD*L`QvE*XRCmv#ai!(9;Q)'
    '0h~C&3fq=GX?q3p&CmL)w<bh^p;_3!PO%^bKRMcHM`m3qEmL?@S?;2XFFFhH5y%H?HB!>LU(|#O%flGpqqxm&Cx9yB2?bT)u>epy'
    'sP!w#!5nGKwCdp_MRQvNDd1UG1dfz%QrRlEB9ImlS3%l<S97wI6N}bJ&blO;4z31WKG!zUBOgOM)q6piQWp2Y1q&r#*Vi)C_d7?I'
    'Z!(V<8p+<qS=X{f8`_oenz6JU!fT4K&Zl64MGq7x3fj=EixV&E^_}V5fldn0h%}t&rHVwpp)6}Ui5~Rm0}y&d*A;BJHjgiY6lYZw'
    'PqFV?PtmGrsrARSIa1zBY&%NVHe2AQ_qLuhYhfcsbvW^sZyM4c{;78%^k+{c*v2B6_=YZ*DUKB?F+K*NTWieJZ0+Kfl7)c)b5POx'
    '96Hd746dQbnli}!Fo#dLl{MBPMm!f28?Q@*Dwk&$RGN4Go_49m=WHgWc!S$WUQh9aO<y|vXAKPHrdO$Z<O!EZv1z%D%6tZ~bc2|0'
    'UY2*b5}waoRU|u9YMLpc_*S@TUOCLuk@?9vpabhVKZ#hv^-RHTVBO{15w#>7_VsW?Ycz~QXUGmqZVJ&#uu;e^%{At&<REEBLFgT4'
    'z{)tBvIQc`M}^qCzQ8Gq3j2bIm_<vL1uiO7K!xRO=Qj?s4^e0IY%6a)$aI584aqweP<CXHx~K+|$>r|81>U5rvTsm7^H9Y649y~^'
    'Rp(`Jb6Z}{H6X?sVE6{`wG()v)EnjZHdK5<jM40cUZ1S0W7l*Ki5WHlX)z-^+aVLEpGd;9@M|oC=mz0T55@DD4<CQ+bWF{lcm@v('
    'BPs&f_O8ie(bBg=hgO(NvGweG*_EUQhQX$ieYs8{yd$GFPP@6<ymUq~wBq)&^x<;dy7e3m$ofwEImxx2-?}_Z$pRzUhqZKk>Fk-0'
    '6}n{H*DJ!ujwH!s-!hBlOp)WwlPHyD+p_V?>T_#P8FA9Ziy#-y9kwlUtk&uP#rBYs0Z+Lc{IO7;RUC-h7N#(su<JJ!TCS)|;o*Vp'
    '+H3~Mvy^aPtnS-c1f3<wa-kJ1KhK5#u89DvWIMNIjgGPUZM@OE3c!`}Ids)>;fI~h9FHAb)Oy_38v{9rp9xWuc7E3b=C-c9tb~I_'
    '6-FR#H_Bqv7Jd%ytB=&`@OUX76JB8Px3t1t)a@=k&N{HW9YmQ}@^l?TR%b~S5rz%_mI1lt0Ug8bAlSCgK+{!lwWUh4LL4g2*LTn='
    'h4!@*cy+TDPxS_$tkpYN?9~yxdZMV<k_sj^M(-_*v)9czavN)x`rA{r=-#u#%L48+R1qa^nznG)R}j_Xlzc4bGbgggwh$qQs+|WT'
    '<ba(l*!Nb6RcD=fKpt`*AhEO^SBUf7OacsYTdbocn%v?hXi-6-n2>Wp4mI8aDOJ%%K&v)XkW5gIH84kq;Z|rRM)L11qaUy(He9QP'
    'kDm9{#aa}MD)cQWVOyDH!}v7UvxEx9iF<h4+p;w~1F5kjH&UWf%{4T`g~%f4J_es&=<ZLxz8?+VXu#c8S9NH>saYTe{A&4uRVg;@'
    '!wl}p4VN5gs)d>>ip!jf@mi^K`*O|?JQkO4Rzm-WC{6XH<zN?*)X|UJ5{Ul0a%G4Gk`K4FD@At-vh+2D7L|%Mv2llU&J5T><a{;$'
    'yltZM1_{qed9CLl?w47IS1zik*Fw=k(GH58V=6EOeV8^b2N<F?3a=;_oOPLjR+oc);=Okre6Kt_(f&q#0;Mrh2J~Se^RGO(g#I_>'
    'P+x;%CW%9ou-6-i9e|3a7S}Ml6x<X|=?2!{^0||ntb;24`(#)zZ+>s4#vjMBQ~~UqMV`WGHI(qt0i{!?)#0Ec98O^<kP3pfeqT`f'
    '9V2C6>TuwYzju^@el})qW7om|?pmP#QfC*3EqZN5X>kEo^My-dx#m>kfx6H>JQx?mp=*XKB+c!$o=7rs^e5WKW!DHwK{oP0<oa!W'
    'X<jDl5m^gRVjG))@+FSDE|^N{$YYS!iJf?q$^dedEG(W};y?RSUWxHg^ekLFXQDn~Wr4Fw3zC-Y$HVXV@+-o}BCeHN@tHjqL_!Z{'
    'r0&cinEkB~gU&j7V`W$lU9;vPQ8%9Xsdr7C;-|4KGxg8W(_)3y)Xjtcu%oLAP2^8gdzAJErzyzYseTjn2TIFYI-EU<6Y_Bwit|*o'
    'RO?DxG{J<wFbSJROW>fIb_y#`bc+si(?d<Z4cy5{9h@>+by=wD=+zz-?9|xKWx#s8#Um9*hdM!LHe7#|E~a|hD_2mn{h@kE2?O2X'
    'YJEnp4DJju|0L3WD^d$8C45qUjdEhW;Dy=w73j(9+tOuJNjN|9U82F&O1xVme?%o+w~}s|>kl}LaAR*gdR5qcj0Ab9spUOAfRu()'
    '!Wk^tz_A~*`x~|9HztQzNah;|o2pXL?m8T(dfW2M)Pf-u<r%^|7kYO#c@kF8P>MlEcZ{+;WPl{nqwNW}Gx<%hmeB_XJE|Cky4|wa'
    'o(UpQy0OZ!vQ_DD$u6u*<Z3lrrcx80{ya1R6TmFKcn+DcN5#>j?5rRe%swbkT!nix3DY(-PSrM=)si`dwkp!yw3578c4l?>^JNpY'
    '(eRb-<>(?V#1>_d_HNa?;r>SN?M$8Nr}NZdNySPc78Hp;((l)&NzR;UZNonwvi1<dZ<QoM-6@uo!MKz}Z;E<n_wjX9PzJW}z`7Qx'
    'TWhDB^xmoDIJ<>x(2aJ+Ij6F@-HId>d{ELl*->~IMP9_GSh&WD{8;SVn$?wwZbJJW&c}e7*JJ^mOT21DW_a#85|{=+09t0w;8Bs9'
    'oe3+Z+QBSa#W*0#b=ej4tO)DX+`OIBdDdWCzc&n)g?Rw&WGcw*2`R)m2$Lypufe6buYWQwp_?q+bdqG78&|Mveq`%kb{7gU#XkMY'
    '*vd7vadct`5mnJnsEt4@;Md+Imh_p0vRU~$SxOEb!34aBS9(#QFfRiPuBB0S^6;xWU$zZD1H6)CEThpkr`PnRyi+jCkQAjVyDf$<'
    '2$NXI$ys9>wl~SfOe+R6`v!_c!b{*qN2;$cCp2^us5PYqW`sJNUHf1}cGcbiXmNsqchFW}m6J+*PE(HSaMKCUSs!|C)tMg{ZQ0VJ'
    '#_$HZsSjb8lbOX?=mG}C*^<k0#INh<we~FPq-oUvrqLZa&|oOjjMKQJ!9gf@TP2G}7%H0PG{g8fvL`deaW=)48Tbx!)R^o!McB6F'
    'l|+Qt0uXX6M;K(2ae)UaTdL;x6D3|+Y!lLinXk#n4lc8YE#i=k=Bg73nDX9{=gNye$6OgrjxeR<+OQ11QIbX|94)hZXQ3#yB&P+)'
    '3@bU5GrXT@QAm3Xvm6O_siYsGi=W@+eC%8rIe3^pcH>eMfG{IUpl2UYsQ@6!`R~SH885!(>9zCD+Tth6L?y-z&DEvG@oTDq9Su$N'
    'jOB56Ks)$T%#GS%LQG!e6+P7kgH;J+<fxl}&()Z>{%(G5iHPNxT}QS8l@avlxNFpWJyRXLBY3rs^G?0g&IdIf&nWwyebTAsyn5Az'
    'BcI~K!{mJ_IlR`McC8F@p>QkAVQRq$zi$Fl>gL|ugzWu>Lu<Ekcy-L*Q2>Dje1g)@Hx+DwR}jkkdfg!d=ht!>Z$s5POrK{cxOVY_'
    'OohNyY1E;-#}Z!F;<$UBPw2R_NQ1MfyWVj*H?`?0(s6#>w@z^mv&wpZKVp7^(A{$|5DOwA_Q_FNdH2rf6oyp7>S_s#u$PVt$rl|M'
    'KFaBzx{%zI7hY_$-*8GK_ql-(DJOy=J0(z0Ie0#X9-Tu?21xI6Bz!B!3c3^_J7};UZwK~c&wVgeniV+8D*5Qelnsx!v`uaFI0HWR'
    ';5z`@cN>EzM;*bYM`?*5CIIz<`1YOXHr6IE%Der{vgyriT^h$%K}WST$pOvZpewT?aLXrOrlxIGkx7cf!L*zz71o;OA21jz_e(F?'
    '{n0!v=jl|P#HX_NYJl%ndPy0`)3IWA$!O&was6gfe4wl``JHMZJ=WaGOsaahL9U@8Kq3Y7dpHVB%DryIQf@$qQ=T$R^An-UsNsa`'
    'b9Y#Is;)cZ$PWWL`v$t7kaMkR=ypH#`R4R8Ju#X0uhOIjSB$~zXjt}blJ3P5>;J}A3ooj^bopS#%{tE;o}i*$X`st;j>u22_g^99'
    'egcwzssnJI7TboOtNf=1r|XUKc@FnTA+_#-$Z;8UpF<6V(=YVg|E|^`I1Yeq;#a!x8)MD8TD6W%DYTx{E7{cMr%Fde^9<M^20#WG'
    'jY}0iCvuj`f$*eSkf;}G?8icG3M2?H2Ni^XBO&n>aRkB9K)URDsIpq3h%9mp8o%bbk;QPb7fttNx@;L+S<z3S;*80DB(%4kfZrrq'
    'YxEN?*#F{@@$7x@yH#t;x<G%v5gB38Cbq~^<Hbw3*qklF8>?lbqfI$<29>{$@OvxTiAL(<+_Va=j~!x@`+6VEfyn0>O`QE(hq4=W'
    'Q6ZZ|aHXxZTCtPjS7#b%Qlbjg)E&+U8m=a4)|;uvL+_td!Qi!|Slz$S3(4)<#x`?)J4dUEe7Os|;mGUmH93go>TVS91Y`A9aM=W1'
    '>1>@7G{T%kcA8B|HsXVrpNW!`ECO-pWn?p=n4ny=zc_T9EeZ;#FE9-+UeGRn29x%<+*%MRo!i?B5`*|VfB5?JMYH9@ynh2LzP$&a'
    '!q+FYC7|mT9vOP*B>l0M=M2>|&}@Vve&&Xd`?=%phbBALsIZXeGIW%l@ASmht7Gn8q}z5T{Xaf3w#Sc|MSQ9Q_I6BkD77Q$U~!g$'
    'h2QO@EKy-?^CFlA5^(N!`0&2$nY`6_CZE~f0uZ??>2l<%A}s;bOm0_AZrV1yr~4NDz6?A3TrNd~GB!{iW%!YsSFmV9lk(U&y<SNc'
    'mC|vzJa4<VaI(`sG8o8)5K3kOX>x4v#og6<xX@Z`?qZ?v%lD6;KK${Ir$}d;3_&&^6i#QU5kY-k5aJNbR5ca{p*B4`Dn2(z!8meS'
    'P6e=EQMoNN(&UR_L}bzvUuo8_FyJwG{wRu_Y}pGNv9bx?(2@4f`s0;PdL!F*HT^Qx)v{6w-3QSeq%NLLw770NbC)~>aTHdCTH)DT'
    'V;2#@Uq~Jt=DCM8?S(8n2bHxwR-X9z;)ms>kXU-YT<Li64Y`}5PSN&gavu|i2K~)p`o*r^Ko_lEa+|QGtVv=iPN@qFK`Byk>T&UA'
    'LxyJTW{v~wR-i7<FU6h_5R_8lHf_Xoe8NFwaSG<U7mb58H({i`nJeuXS?UN#Opu<W*B!;$!hyBesXx&e>}2-vF?a<rngf&>vXz!6'
    'UqkXjU)!rH2&9rFa77T;qB$xYavz{`lxmwz*CGM=mTcSLL|~7wZqPoy!#cUn|7as<mrYljuoVEVKX$k@4xOVyZyzn5(KR6$Hua0-'
    'v@O_OJ@tcEO21sS++kZuD1gzc&OKl4nrvL$pQVRC01M>taa(>$fXnBg^bP22OI{Vbd-#>9%YT;ijjg1gZ~e4@2b(-@FH>o+RPCXw'
    'Y6M(Z0mj|Th?mq=B1GpckWLVVqnpwtP-1?2IGrP@@8$S!i^{BnY`r&V$LF9`!h+?d>GoilMRuN(qOlr}t|kh-eTRdc^(0fhIxEA?'
    'Bt^EL-)<0{$|yoYOo63=fctu+ZEN34iQc!=91Si!Eo?`&_LRFX84C%APBxsJ4O405jm=O<*tVAz`+Ctn6psr;Os{AP+8Qro0W6>o'
    '8XFoZQceT-s)NAAr$WOPq;OMg!707+lGOn*Fj~25i`Dd0BV;smof7WLTuu;+goo-7HE45^SD__Otd@ygWy^b)$CFYm>_tGx{NQ#Z'
    'l|TQ0@H#Om0n+<Sy-i{G2@X~taY#Lkt@|4Agl46*TmC2Nu=}=km_s8T)#pTelVk_8qPfIj{&R@tZ%?1!e|sWs=}e9J_>ciCecpX~'
    '`b`g7Eq6{j)>=SO?X4M14lj#PHV`+Zhpx&oPu59KlIN;ya=0d|YqI)V5q4~U%~aP+b<I>WWvVRD03Bz-OgX(QS#~wn(+l~ORwpld'
    'O=;JZR>uBGEvE``pqX=2ilKkaWY<h~&18QIxJNwu`EZ`AU*5rn_HhQwePm7y&LEkRxk}-_<j#ZF<8F0EZJr4;u996PUqU+9*;JSN'
    'p;wdX8rFOlKH1B)^8fz)<^LOAGx4{0R!ZW;E4XFe<mI19-W1--hr7e*gI`A8%q{ctpI7nzw~wFSA1?Bz{X(40xnKJIpS#@`jB%6e'
    'OnmwHkAHpta{Pp~t_0Dk&BdE#eDx0h%%5LMq{HBNlfQib`02wRKmPK!?*g0oqxbhhnlb$T&fR3Eh&<66;{!4`@x6F&ef&n^GMYVf'
    'bPTWPRPK9`mNF&me|Dzd|0D2w;q*ANFP&V)o)7Y4Mf~>d)Uzu8<%#chs8lQaZZ~9qFt-T~yg7s8tAgv8a&%*DcSz_=qIB>Dan7I&'
    '6oSf!e|k1I#jcRrotxy6{B4Yi=@;ew7f<){**Yh%B15LrAK^s1rCcGMRqH>F@~Fao3E8*gGwft6U3EsveJfc;y7gxy`R;-GDPF$W'
    '6(ufovydmQxN4v8JEUfs*USZ1xw*-*I8RmA!c0#&70+l|L3@7J9P+zA-yeP~*;nY0LxS(5M-ExgAzfb%$-P|PE1DnRqnvHVvq>kD'
    'qNIzVlIrf83Pxr)Z}5NGW)>0rUI)$1!lz1g`D3>mqmM`)>a5vb_z{DmPd{_@bKpmENT$qV{M-UtUq6D9Pz#WIBfYqkq!X)$L>&C1'
    ';7)RWKCqDCICbkAZhC_C7vjy3GkirL>fTs#VRt{OB$eJ@VE_!2x3dLBN?Q39hD7ifFj@B^Q(ewds0iQMdw3(AsFO8YetXSbM};@v'
    '^;2Cx)wP#j)qnr%Kip~Pl<CHdo!_{)AV@Wd9qcQ~7Mp4&8*uo7<|8|}1{&Cg*Q#jcC;5AZhga-F!gQikj%}YzSmKl7%a>(<_I`J{'
    'vGZEuz+X_%l!P^AfSxmKM;P?6WoH9{cOdtHQ-wJNb&9P5H~RBT+IO{Oe3hlHC~2<(<t)a5tfrv(8MY(Ti7FpN>XLo9RdyG`FhwM{'
    'VrVEiJ>sYp`AlBNbI|RzB}v;JD7{>fBa}~%s^T1OK$;9GTpMI4D8@^|((F2fnt4=p+nhCGokA(~+ge;^6qhnMQsPbc0Ug|)f>O=j'
    'cj?jjmA$bf+pgYT(bq>8COY(R<?ObnauXRu!IhTv&|7PxFv&NtDX)z7ZzG$uQdYmH%}u72!l}#%<|ow_4l7+k@j5K|UD7>M%EksS'
    ')8?h_y%pBvI-E8ZwBugEbc~JEl0B~nCcsitNLtAa-V#h;_l+cPXLybH5o&O7d8-&)P7g?6F_+a#!igNpu_DV{>@G81YPzPV0c`VG'
    'k#blZd_!6zFvUwN%ZO)Pe<>3OlV4?n(Fi)gw!G|_X5mstFwYGAe$6xVlFeDE3Ak3ir(-^Ooz=FS!p5q36Hm#*{7q#PsYqb=DQrq+'
    'bd`KBDOjUB;}d=O9F560yFzJK{l=>1-d`-kq^DGpVd-lCb>v4<DM`9MV=Q(Uz$=kjHTi^Sw^*9xB~TllNl@kpw3RFmt~ak>Uy3Kw'
    '5uI$sZdKC4Nfn!!{R4Fvokc%cC^dk-PYsdJF0+k4yfv7bX(AaTODG{gKKm?LO87cIe0}=TdP)?+KHaa0hFYS<Fu6Cuj2}i=1$G{X'
    'mb{-_hCJ(Vab{XlB^tl<brS+7hY!Bdn6AZ6@43NSyJ1=G>=t@<Dt0p`#g($%XVa36-7mQ;yTTNNevg&SQDM4Z2~SPu%dw*&xgZ*;'
    'OSQ(QFIWT5|1>>ZCpJ6LDdKcX|MzcS-|v6fef|1xtR_h!p>%I<x?n@uF$!hX9+t0pt%7G!@4@$^!Xnm5lM0gb>|HdF#}49;BygcK'
    'IlSrAs#koLy-~l!c6z^<jBkbNeg^lB?lUd1?o4~C{%8&0JGDOF^w%!UpCQ$E8XBdwh?d0Sbk^7X75OinSXZZ~JD)Z$HH|Rz^9OA1'
    'ZMwIM3`>`Xz`>S6i@oJvcx{-)8pV>w=}@}H9$(4Xds8s+_-SL)SU88vI^}$?nb)njEGH)@=;9&&q(0tr=j0PIEKg4_x4muc`wW)6'
    'naN0w7(u{W4&Uj`TM2$^9C)}1{n(GQS|H}55^kIP19XA31#?&?W_1(5*iBPfSJn0RRPmFR3PY6z>zM#?ZzwXe6%Fry`Tp_Khd+M2'
    'h;QFPLLT}0W3$tR&+&7{;Dt}pwO<$HYYdVl%grhg^0wR+GWA)L!faC8>!BZ8xD3x--V>~l`o`#KuY>bZR%B4QZ^opWOE7e)AVJ$!'
    '!LARv><0&92Y0Mn{pBAP6*qFIg{AJSXsIv%ga=`IB1lz*v+nTC?g^>$b{TeSQ1fJnuO-9-!?=RxK4OWYPu$s9xR%vgbS0lz;dm|F'
    'A{~`4i_R1sW6vbbTP$hbG}&+mlcd~7PF+w(fdiGe*VKY%-zUwbv6<iHY3PqVPc`V-hqan&SmkbdB<y4x)03GU(!tiuY;1qz&OcfR'
    '@o27>!l0Y>u+NCQTp`pJaJ0ijqd%&d{H*5yKEMBSxBKE%Vim)K`G2YpF#XM~RG`QJ^_5OGebPy7;kl%ek<lTgOgtO_JrBL(;8jBP'
    '6v5X^_1AUpco57~1$G_0P5gV~2-G*mlW8+B^r;f&zr|)#TY8iCoZ@gxI)9HXS!E+qlVnmlIPPe<ZF2t0fv<xrH1C2E%sVyPleAmw'
    'WNrkwROL#+dDJFfq&W~uHvaw3KK&aO4b>`=8W?!KF=DVZqQA<S%Rn<PxUEP5ODt+&76jwutKX2~2iJ9p;pto%p+mXXP>L$2<pGC!'
    '@&KT$sXB81dgti|NQ+ouk1p{Vp~pIB>Mr%W(h$(P=Su6w{=0STixF<&Zwi3>xYGY*7)o-L)>HKJph(<8V=C~vL&#qF04w6{*Dpv?'
    '*(SHFUR%;-ciI?WLAGlT0MmUAzEj%3me?2AzR6WmTYgoU>T*mJ`5qEizAf%BwzzCfzDgtx)j{iawI1~gnM9nj=l0e;;Q{E_=Z~NM'
    '_3Z!OY)U|{iGSm0!;rm$QI_p-K0Ww!&psX^KfEnxCP~GI^Pr}iw{HbZ#J~Q-T`^|Ug3>MkhPph?jaE@PJZ9dcB(r8Gg2#9xrbrzw'
    'MdEYFdrqD~6v|U6rk|r+?%T?zKc00h6C^{1=M_ZYpdZO3om3Y=C1?vNrz4how6A^!ybfX$?NO1w=~;`^V0h3(mG-ek$$2YtC^ta-'
    '(CVjCfSR(@D=3TnI$lF}mSlAMq#A-ZOiIz$qhm<N(OH&$s-lR!PSkLsZ8Z2~wNu+W+O~id71?|(Jo+>)`NnthMl3rrZ0N&+mr=^1'
    'B>k`u!!D2qMxr7v5{5}?S0|CG`?lMH&Z1d?y38Hn$8WyRGG)cDQZX)3=ihjDdGrK5`C|8hs&gA}+@<z*-gR#$+Vn)Q{7lPk1R`}M'
    'Pc#jdI~_5c-OvJP%8c&kl^(L}s-k%|Mg55V&RuEmmZHa?{p3OE%ucQdsR=~vHIaJv<X<!lAiAi0llt`J3kn_u^E!8{{F*xTdi2}6'
    '2{TT6i!v?#8e+ti99l#UO~s9r!q?b{hDNS+-=EPj4hn|Nqli%Yf&{CRJDZWLU^eb`jxTDfNayD)VhlU<-OwMy@w;+KKZDI<@GGPF'
    '9=F;(O!!9}<Oi*I|3eE!*sN+qaGmts@(p_78qhy1c6NYhx#;1mZ`jbNE8)H-B`X*=8C}Ol?a*F-RcbUnS!sw;cN|*@I_>SVPGjE%'
    'Hu)oE-%(g(Zt&l7Th5kg29`y%O0)06DPY=~i#8Gy<|*x1peLDS=Fm1$?m8W-!@e~|BOjsjP!=x}x<IK?2q0aHF%$^Iouwq`^Cb~0'
    'RwLM(J&AZ$t8u&522DK>KOCm_ljnuOn7J=6@nVJ2y72f{`-JONr?0AU*Arqt`#5MT|D*`u-Z&Vh`7~E<MP91sX6o2m!DS>t1kY@1'
    '#2a<K422d_nXQ$<j8+V%#+1Y^3=*D{<PhsV=y>?S=vfi1PsU$}w!LzwIA2_#PzL&yqXR^8R8`k#UrA&*kWA>U8Js2-F&nJPq{{gi'
    '`W3?oiVd--;uS;e{Ji`0^xHzevsBt6jNX2Buj7h4hd;j+d5AL~0S)!INdR%{(9Z;4Hza71!%9k`elwySl$3>GJ{eoe)kbZ-xQI>@'
    'p(IRM8_t{1kLg8jI9Vl@&0M>!)K9o#`4`m&C|M=jH7*j~z#dyB`Gv>=qu`FWjDR0RnJmmcYgtM?72MHz(7>8xSIjTpKYse~$Cn>f'
    '|96l~EIe*=N@OyI%f^u8W6}BFul<jwr!SysMd2AHZKM%gTWF<|Y9<BpLc6AqGM}RTT(#Fl{$HY$4|0OiYQVm5vogev1p?r%Q>U=)'
    'Iqpn<{PeG9|NnoDm67&c@X!+r%!SdOqh~g<V%LSSfRlO<J>kZjJj|a(0Ze*GPhx_rLcKfFM#=7e^SS)cGyP`b5``R+%pN+F@<HuT'
    '8@ar~*As#yIhgc}YmzK8d5hH0J-7-vouuMq;Lv#W30k&5QdjvRV_p2tiYO?O@Ev6_FPM8g^z@}l!3*N@`j_!PbCYEk1i*draCpY`'
    'dedYiz1K;#Q4ljLAG3y-JK?g)_`Cn)=YAAlAO3Ebx}oAqgZA%Z|GXn@8HG&^U{n;cr$R!Ag%KD#uAvIJjUrwncz${FZ)IClZzqU0'
    'zgX*(S%XVCV%v%WFKm4@k}k9iqLDk(`3Gu;g^DTMR#tr$DUjHm9R`DuEk0PdVIK647mDUGAQhW%HXtPq=BqxXqAPt%1ZChgIyID3'
    'Bo42?T-~s;ctpXPHQTbVV9=GHs1Lls{KQ^?3U$v2f^0=9!b`)ERfuY^NRZh%A}$I8tvRR1Y3@=giNi*=EESHNP?CX2=7h$sZo$%G'
    'XEviKBL)~E4GoTc3zVoXUetHaXFhfOsCyB9m}mZ`*d8LA?HydFNzW06Q?l~J*pvm5J5#KR`>vyx)f@}a5XyEQ*-9eIkMUt^*ojmV'
    'CiuX2)}0DqSLO+9YlUDhhy9n*zK}e?7uqbg47;Q*2U%*7PK9J~CvX3eYSp4`Qt5#V@1~@*!Bj2XT;5*KCTQ_WiG`b?p{qOSr1G?}'
    'eTGt4Sp^`HFy64$8r?Ysp_1FM+H#@|#NY<^FEtFj7tVpMB)(Od&Qc^bm6M%HU)Fh7No<DBU;O6I(5|j`Ge7~fmXMH4Zgc&S*jtJf'
    'Q?y+hIxV*?YVnyes2?LcMF~|s(HqENR~Vt4Lnh(=>FIe!zgzsxrNh5Ny3oPh{&l}aiJXNC*5Ip;_w1v$_)w1WLN`vbe_j6<X|A%q'
    '&LTJJSUtTd9pcx2-9}ZIdlR=~Ysv2_sm-#>R=8Cg&Qx(T@7;uCrxD9qTrGm!IUUNw2HT1Jzm%j5|A9P{e8NlILfFk=vUDxC9y0l<'
    'ma)6$s73Qx&YCm8s&ZpUU09$%1UZO?g*7T*QJK_$(s{_^-zsRR>b2>vAcD9aki;id1?ic!d+qor#G)1_L=Uaz*z~Jf8998_=%->y'
    'l5+OT6bVPDzCwB#4SXyR>Zm328j-5#6oPz}WDKGHQW9aC<e|;H|D)2y4hK`kSokPQKbHH_$v(KhEG)PCQH+dJUzIhHE+-549l~Cf'
    '$JV-Ry_ipT2$DF;)%O}7t8?hycUO45&+_VVRz!bCE1Z2fhM=j}RZS?7KoL{|&LW5}<pp@LMqo=F9RZ=(T$DUuJj3T2Fn%Q)sfJ-w'
    '!LddGpk*SJtD-yh6I^6YOz}ad-uqo!*FBU<Xp|in^0?UV5_^^5u^S48L0JPc%w!uP%zKD5rsWswX$%_6tPVPAEWOVCo#cXPYxEin'
    'a2jvkzAcYTLv>^*ZCU+hI-41JGO#p(K_{EVGP^7W(uwC*L7{M^uw3ci6YyxTkQRzbR8fashXQjgd56y4DDodi7x?1p`K|`nUltb>'
    'ju6@xoQPCq&r>};ZbGXYw%9imUPdg^`OMp)*Hq6MA~oOZK(oFMHEeh)oIG{locCM*4R&|1y8=%o>JhFp^ooUb0eT#1Vk}5X?Z3W4'
    '!BLK}Ue7TZe6UU&_HS%SNYM^Y>P1EDc2z|!3Z&U9Z_z44($H8k@O;RtBmf*G>&9VGH#s{;!>l@@=bYrt++8g&=Ci=aA!A{2%3#e0'
    'QDO`t*D6;Ho!Z`GqIx*Trc+bME(-=0@yLz^-4oa!M;BkJ&o$arO3MbV6uV{RII;vW7*Ry47DX2HE%wKjD#fq#(5U2Hc7Qh<WVM1t'
    '3bK8T_S#n*q^M6On~1px!SZ2jN#}kH8uI<Q>T6o|yJ{1dh(FP`IFpf}goEEw7!PgBWdPOdJrMyYOq$J(x`p`DUsi<LZFv(2t-0(U'
    'jJyh6gbHfNz}Cf{*c??%{Z5*LR=jc#139ADKrBM5oScYAe?1L{h6;KrZ_qzr%a6818}y9mcjl9eqzh}DDe4mTL(qN(4#g3tcuQR^'
    '0ne))id*P*S2t3NZXKKQ<Ez>_4PB<J`Bg`Am_G7Q4qG$_!O!IJG6NYyU5EH317SRMdfBrTd>>~x;V}Vq0Aa;?&>@abIY;T_7|yyR'
    'O%5#|bTr+x_(aRHR0w1lFzyC<b8I<6V_Ee6<Q|@v(vXU!PZ?xZ4c@krq9dozr|T!{2y+hh4qBuu3~_R6+`w>xs~PgDx?r5!18Mi`'
    'uP^??-IZ6>+hgVwQ2Y!9=Dv6|;jkFUVMBDxsgB-ZOQ}<L<=uGpV=q`D#r%!?>3(M&i<O1uX3{qMh8zhwc5H&3E*8_GNbG~Jo5+Si'
    '>{yKA=7J8`WRD>Blvyl*FBXobQN7|p=XEX|Y$?U|tj>gRqbwYG{#m6#{nVOEl&}|cU_|5O$T~zf%<}m@oWMeCLPx}|zFT}6lB=56'
    '7fIy8&Q?+_!92M<iH;);c70X#Ryetn`8cpH*CO7%B=_yidl}o5FxgV-x3l0a8;EE1eIOz4*QpzIP71AlA6t+=K79POyvfqFPSSdR'
    'x5TTZHoF3Va5#PkoU-ODsn{T`kk8A=O2X1j;$7PzZEW`nGRR^`_(EA*T)0F>UlcmkiCy*K>(dvKTXIo^=;p3PcDuRvr?*@PJ7^&L'
    'rUjy9P~Qke>;Q4?L7UuWlSU~Ee3D&nmZHd_y-Ai>3O1bbT!<zSSmgm#0IT0Pr?5dz#TJ`*qmWYZD3GjkU|UBz_4vZ=@GSB7-@ko*'
    'zyD?T_3OW%{nrOkK+@jo?7UD`Tj^!3aH5_sLZ!#I{41tgl2tW2YV3wG=LG$TlgaF_bmqnWbf7f$Fr}pxAnG0KB+ZHor65Uhyo`ps'
    'QXGe_T3(oquwQGoEW;#3Pl}_6WtYiyLQuuq6)-OAfgy~Ui^|#1<R`hPwuBxXrJ_g$^(W8{xBD|xP#cuU$cAIAB!C-i-_i{p{5UOZ'
    '-k?mu8R>N3VA4|c2^%tO;oLtD<pyDsfbvaZ_9QC=1ujS??b<A4C~L?=F<JWvzzI7W&qO*CAm`Uw0fw%FD|EK60C42uhgGh(_;=5;'
    '_tHFi0jE6C8cIx+<^s*?v;#~=54_M!6#D`L=u70E#i~E(?h_6Hw$dg`5QoE86|y8e>$qz%%a6gR?qm}?wMahS$0J3Dlvs6P^|c=S'
    'shVfXYS^&aBYyL}{^#}Q>51O%?LB<@j0TU-;6gGNYzn>Fn-NXs=XnQiI-;K$J=devr_?f}q3hZCJmYCVhIOGXbA=zO&s6p5C0Ztw'
    'SdM$}V6$mTM>43>sGB8KDE`$jNFrLD+eAC`4Dx@ZWSFyv^_(?W+AvKMtCIhb_WO^2<?Y+Ii61(PAx{0;nRWN_*J`SDEt`|B%FeyG'
    'O(~Y3dYCXBpZmH#MQ0;5n>-}tXflA0B6z?9x6=Rkx(;3I@Htr#FHu85+GK0c8Da)sLp@Qo#x~))c6u4F(nlk=-)!ucgH^UmcHp{h'
    'n013*6(Dy$*4|P1RoDHd(Ym<+fh!i7z6v)CUFGw+&hV=Z!VL%keHreL)HGcD=7DT@sL`_J65#^@FuyBZaN%dWuQ$drummX+V5v)W'
    'MaoF3Ksdc?bv~;FqYHM>K7(M0FH}$xJvk<#snPXx*a<1mcEV=t&9b8ry8|R1DEY(iyYkA$p=Y6k!oX&XZqi97Q5X`k%5#krbWc{`'
    '2i449tphP^L7$&h_Vp`mz#R1{3keNQ=GP9<l}H15Sf}wF&_InQx?6*{;=Z1n9tL<^B$RB)jkXqyFZVvFGHTCyBcsRv2BkE*yRy}s'
    'aeGboAPg-4wndGmOtRWCN`aOYTPA!h&y_~ER9(lTRqkLpL1@dzvYBX=BeL+p6?s58j0lz1rj7PTvd6Nbh*Qp<DthlexjU_VRU;8v'
    '-3$ti1T-tMn*C(&asl{T9T=^N+75_Qm6n22R7NPEALkfvt7rP<pe2(WL1n+2lZz==4-D@9ATtQfdR=`1f)82Mkd8^D{%>pp*W4&U'
    '#&TIKfc$n@!jax4ff7&1v<I;75A{b&Gnta4T<)h(2u?k5Cl=g~SM&7=`K519pWlCbD&x|{7x(Vd({IEN9dd25_j8zRlD~7x%t6M3'
    'Y-L>T*r(CI`Qhu+7bi77_V@X$#ZqoBEPz@!?JE^`rmN<n;-ZZ;>ZUxdQz-dYpz3ih!)+R_iAuBeoGz+izEFRJu}pB=lT1=-p7qG;'
    'U|SL*Vmkl^mVj!i%`aqEl8p?qjqI5HDWylO=r)`ZtpkxcoI5P0d^z&45q{s>z??)k?VBod^V0C*LK>C6KtWwfy#gH0=CK1^1P~Ax'
    '*eFW@W+kG0TcJ6*g@kmipeL(^Oxt(*_jJ9pO$*RcssW51ig_gqSSlgRhoc!(a-%DU$xls-mF$?Yjm*^av)an+O{;UhrfsIH6Y00f'
    'swSE~bpwaBmg&t@e8PHQ<oSui?$*%!*oD_#O)m%GG-W6M(%{=Qj`6XC&2a+g)U!^68)PVHqHnLJz3p@Y9-pwC9>V=q`-ZBG&fuCC'
    'CVF~WSo+hQqRrmAXG&^1vz3csUdM*D<S@P$YU+^llZnji1ntP3$CF~R)+4K_V``!6txVCK8)dN=9DQqwJCr(&_RhOBxD5{WIit=7'
    'q6>HCrYEV!iGES^=t3g$9h5*{*OMgDqa668{=csD3_2QvS`%o9p)~?|)o39R>Ev(9xy<nzatb@`wjRUeRR_dqMelS=q}A<}=6t>C'
    '@>M>X^JU-FnYhjdFJ$W0JD3vRB~qR_S%lH4cid0i`e$Js7)cmecGtqHHvO?lRb-yA#DTh}3{sLE?(oefWt5$CI3+BfCA!tyH0ua4'
    'LIveMQNruo>tqNWvv+nCO&1<4!ovQ|752Ae1;g_meM8Btd<1z6g#l*afuMGLNtQKfpvj8NlyS5*DRZNpteMNDfu+*L{Lf-qt*cDe'
    '=Q%fn(;rM`cF^lw6;qY{NCN9$w0)_o5}lZYgNI_U)>1hCMbH2axArBqR6Tm1W^wjvKCP>kS5{*vs<qH*t<0>lg03W};I%!6;75!3'
    '4mb*J^bjK5yghtQ`Q$n4-c0YQ=+KAWRM9zuQu^l_q{0q78U+?^WUA~__5_WVzHIkNSC_%s4!B0B%rbjlpy$Dvq;0sL0`Ka+b7f!|'
    'tI_RGts+>v5_YQS-!?t#qr<peIYb)P%|XF>Q_%KPu|@jDk{^bpcBXqbBpT3J%*LF!ANofRnZ70x=iBc*#>8i~z!4ts^R6N7Bpc?l'
    'W9D4Kg9^%GmJvyFx2ZUGjSQrp-yR&4DR<sCHOpXIdS4a_bv*E9<lJ69)?C@NLs!*^XAN-a&M>mJRP|F!x<#LmJj8Y&-fkN%m!+=5'
    'chv{n@C1-X7D#miOFTOqK6B(c>k(OwNp+OZN^51JvrMf;cK^89Rd-G3=>$u0PMlzcZA+i~r-It&r#065IHJhcEU!T)$&kX=9Bs5C'
    'v#yj_D?F+!w;aY7orT#6<b$=kPHF8uYC?r2nhX$b+)ls~V6pLpf=Uco04N>o2o&XDjumHG_3)9Rxo?9M(XA^2N6I&;E|**KNQ;Q8'
    'V5PvTIa$hyRe2<5T@p<PSA#B7aGR==kAj}+y`WSui@oB4g_5u9Ybp5qoukV)nF$V!WN%|bY}uj>?Ml986kz*+{tB<c!g|Gm85=#J'
    'ps;E~`!CMqs8__MlMy<4KqJ!7B9Ll0`KG+AO(%MCq)$}nnO|1{=K4my2vQt=QGmw2Z-GYZ%%#>J(>F=ERk8goT_0|N1L50x60U{b'
    '7*#H<IuB$VuFm|_yAYhTr*>{*Sy6mLmkT?`3Y8eagHZZ4W@@%}af|Q5$bvbzZG8?MXhjCsP-IORB$JrKC)~;!>p3GXm5GhlCEJzD'
    'vkNNCJAaeBR26kLTh}#p%u~c;)0YnaSp(&{=~e0;dBRsyZ1Zm8MxTK|-5_?Qm-Qm94C*si73mn2+Kh@g!xcWHS5owJ>Hy>%&;g#E'
    'pOq{jkEU=uuu^sIh*}a3`+9t%H5$gDGh~M)H-%`W04b!a<{I->wvn`>AavU^U}YTM;sROfqeARmU*MEQw|>Dy%py+90v8psqQY{v'
    '^BafhjHs7<ww1RYsJp?{ha@r!I6yK;T~yS`<O_J;0&h}Q**B=4c_?CjhGx;{sxwEpxh*f}8Zd1QFnj~}+6g>S3YhYH8>(g@#%T6J'
    'uTNIhv1_`AW(}Kww3v~d?T`u7Pb7m{_%)V6bc1lFhvNCnhmXH@I;Lh&JcEaY5m|z4d)MSjY3bXcLo3YJ*?RW9Y;#fr!(da%zFhba'
    '-jPvXsNGy`UOFQgT5<bX`f#~!-FglOWPPXooa9>1Z(SayWP$bW!&*ANboR{03SBbp>m}x6N0MZ+Z<$4NF3a)eNt8;nZQ1x`1;4eY'
    'j5z7yMUV^U4%-$vR_mRBVtdHRfTvsz{#Yo_Dh|YL3sV?R*!7zVJzUhK@bJKPZN3HMSxPuCR`=~J3em$S^Z=FZvItAyoHb(OC-mCo'
    '=gaWlH4$=^?CZ8H)-ja<8;>=wN^qs14qdfeh+?O6|6>O!wI;sx&PNU+YC>eCouT)Dd#@`mE8%HT#S@5Yj<PDXg{Xsz>m%7ZOl-=>'
    'mKRh7T6+C1>b{pAuN_$84kA%3nY)g$tMlB72-Svv%YY>FfS}>_6zofApbaay<5J~YAublz4{*>th5oz~n31y{R`m|1td~7m?9~y@'
    'dZN16k_skTM(-_*``67~avN)x`rA{r=-#u#TLbPiR1r6BnznG)R}j_XrhKgHGbgggwvZ)<%AN<a<bc5}*!Nb6ooAhbKwfkoV6(Ix'
    'SBN{_OafGLd&r|Dn%r_HXqiEws*rO*4#nOAxmD3dK&v)XAWcw@HE@52;Z|rRM(P1rMn7OnY`9hnA3g7@i?t{?R_LQr!u~SLnDJ?@'
    'X9*RI6Zi18w}otW22x{@Zlq|Xnrmo=3z1jQeGERm(A}SWeLot!(SW<HuIkW$Q?pVE_}=mZt5W>hhZ)?H8!kE0R0~H}6qh+y<+W1z'
    '_T`)(cq}g8tb~3PQQGWF3&buYsiPmcB@q21Y`|QPZ-E5GZS6|Yoq{ZVO`&C`Vohw^;hZxkwh%dAjbCt^=)6I~b5dUGIf(mZ*5Q?l'
    'D(baRv{1BzV&|9&OiCZ7jmrUsXpQ153I=CgZ=luXV4ryJT?gMQ4^OneQJ+9*jFbU=SjhY<4=$k}PdU`r;NVH(5GCyO24V-G!m7o^'
    '%q~qgMN_(g6}f!w<R<H&4g@|~*vp&Wo2l`~u`E>pJ7<xna9Rx|d~`tR)QxpG`Ur<p7z(6<psn8*l>W;|8JId8IOO;pWuTvpncLWP'
    '@V~nj=)ct2#bMK4TTxnEiPe1Jl31=e)p(#Tv@a0G1##$_;R;D}d%q`=j2!)m_Ho%Yf>Mx;JP^5lTVI-&$qGf*0+iU;CZK$Y<E{&)'
    'k~;Djq;+B^9;GsX93=~jCztr){*+f@JQO_(7tfifPgq&ttkQy{W&82)JHGsi@Ue(%<yL%Vk0p}O6B?;Ia|mXCE5x9)j^0=qmP6O9'
    'c}UcaXMXA(L2lVr7ofDSvfGQz)PzTmoE3gmHxK?3ldiNhF-T24R@(HO<}r8Y3r^HzD6Ng@aQ4Vn$Y*LOSX9xMt*ejG1QY(kB=#Du'
    'ql1#%DZo9^ayraS4>kEVa3}Ao-CA8ftU8XiM@l<2`*XRt9&hnT#nGWo&^Z>@U!{ww-X6^r{BD1!UXs&5ceq-!(kl%-!|p!`*WZdH'
    'he}za)L*0QTrU`Ec76qV2K=^k8C9~@kIb8Bgtihi*T`g1$@#71Z07m{4maJ{8;@QUwlE`+VrqVRPa`3vYn5=2OEz%q$L#)YulbG1'
    'p*WKH2EwMQRQbCfn6!Zgo@YE4jLs<U5#9vRyR*rqu)!t8#G{)}SxPfNB<U&n1YDl{ep<^ggo7PbutME;S(wlS5h&eQ<=EY-bhu;}'
    ')+KVax-QeJ5FR8wv;`AZExvdTnYl;B(WC6xA(`<$C;(xFdou|eH}qiDww~1zK7}?f(%rO@Oj>qkb@&Bl6SdKRmTn8_A}+*UWkLIH'
    '6~5vAM(^!Ro$06Z_+d%TN@5rki9gcs*QZI&oN2AaKOeI85W;VjB-q_4-jspMltgce#b@^wc2rOX_VU2G7O8D(2d4DispMR{g>}%4'
    'R&+X$ZjH+3b}PP7@Igr{XGh^>6rB;DV&NJq@?)`cYgXqbx(V%jI57i&kjVl%mw43*(eT`LBrpwt0JO}U!80Q@I}=t+wS!r<igBQy'
    '>#{58p%K>4xp@ma;pPdP3@gsi!ve{NC|nsfc+#aLw5h6~>?c$rEi};KY;XfVR}F>Q;3(bK>l&9kP8PK~`MAxEYxQY<WQ*qkx=2;j'
    'Ft3ahUUP1UPE#R1Fxn-y@w5dr=1f6+W}$3WzD|~Mut)F`FXEM6R44?_01<3yYMyKi=+544!_NRcC5ho^^v&rDzA0~A%rZbm8R2d_'
    '=nMKU77lpUM2PL%vN6+&D9*ltB0={O=+%+9?#t;F-2`e)H-g!+4j104CQ#QtKWQ9+Ry!zC3hf<M+31wSRt`kt=5C;aRrDaNGp#Vn'
    'sHEq*;T?HXAHpyJHVbOe1q=#mCYR-iS=-TT?O7#C)2acvq&vf)!BD34r?JR`gHUd@OBRnXE;mgehrx(slV^(aaf+HW@Ezu;G1+s9'
    'un)@1wg|xrAii4;S;!{i0s~yORLzl9N<7fmuBM5gP?M1z#BmQb$07I4RVNa-=sgJ0bfnDkI?^%oM)NF81-kY=gKw0ie+tLm>^5Ae'
    'OD;)|0TRke&i4#oD_URDHq$Jjgk37>hv;JIcsU<Cmqre{rjOmYga{z0i3%UE52#dbkmUS#Jxb!kz&QOk-dP6^WW}k3@}X&8I{Fao'
    '0d2}@N1GKru6YbT(7D1C)2wz#6<P|2t{mkOFw&PM0kRy;81A`p_0~UQ$So1EBDd@GS0FTlo<etxTEb_lgG>>8wB#P~b>gA^%eyb^'
    '%ow&EN0kEDC!K19E#DK4t+NjgxA&z)`dY{2wX*Gn0>Cies|9=hz6k=Wo1u6UV*DEph~CO{*a0m-u@M$r4NBSHR1hIvK`8I*HJS|k'
    'Xv<~1omuZNeV(D<+QpBb6=H6sQHN4GODJcH<L-Grq2taXG0&#%dgt!k=%=Tk$@z8PI>k9mPwRami6Ic8TatsNSP&YqPmVI?yLU#X'
    'Fg6obS4#+zy)<t~D(t`nQ_gJFh2*BZ@M4?&hEpQB&kck~ImZ>*DS>**L18lV=o~^hKzf%W^IJKe(4`33L4$prI}kg2?t`h)tiYLA'
    'NwqJgka#@GZOW|28St?O{{q;)+Zcs8>IgPHN=pPWA*mNmxbH-_vFw6Txh`S-)wfII_$uhAmS#$z`5SciRs?SO<jd5wttv7}-8-1u'
    'QzbB4)BFPlW8BJo(+JOn=4m<Er|Kj=l@;2}O1KP4^DYA;JXSF;na^Bg<KJwGPo*`E(^IX+$C^8tNp&zc4K{QYNVtK%5J2%wx!0{&'
    '%8&klRUTDLLl~h7tKpdJbH7-5s;)aI$xjqIdkeZLk+TV+^UG^LB%NNSC&v5!RhkqQi_xGRUC+Lq*1dS_{onY4aZ5R`uD+c6V8tE!'
    'lO73z+-yRTk{c+*oKpiJBmiC^Z+`-%fK&(IJh!$D$yfPL4c6it<?|fwkwSjn1Cir0Izxv-3a4M_x&K`)WN;h++r+PQAxXxXceRoq'
    'n^Jr}DSEQ0%}<q%k>)|NK~aDVG8)_}d`{#nl|%ALRVh)g*w~MSEFwrGVGeHyp-(~zF5(D+qk(iG_V8`BY!g}J7}SQ%b0do(XD_br'
    '%XHZ?wzA5hLfIOVr%GsVI|08*wASb+T(JMeBjefo;CHLmmVSZ$d?QA~qD^d(yT^-{aIraC0$NrJSVx<3=nN`<AK~{_v=fcg$GK@0'
    'Tpv3WEBEz2qXUu8)1o*}yAEYH>gPf>iQr0GY5HPk*00V9(IjUTs;N7i5j2F)pA8fi$5o~t550d<N`n`qV#NbPFC@2b8{5qJ?HsKt'
    '^5rh<%OkJ5*W_iEtGiLa6O7ec!DSP4rL%QT(2{c&?P@k9*@zEfekMv%vZ&0VmyykgVwQ8!{^AgWw#YD`4#hOQctN}P8BE&aw`)P9'
    'bZ&1iNDSid{Nd}<7tNLr^ZpI2`1VGE3Ui>;mVmBXcx33Ilk~@4p0jq(K(i5w_?a6*?&prXADZk~qryU>%g|AJzS9$1ua3EYk@(x0'
    '^#AzC7%)F(7V)VL*xMm4T5d<u!Qw0h3%}b*S)#()<}D<HmHQn&ye}IsZ#BltXSTNhMD9wu9J#7UO8|AG+f|dBwhiy;zD2(;!wx@}'
    'OA(=r4U|V2e&psAEZWedJT^|Rm!n0cbR1UE+wLu#?DUTe2C^Z9l9@o792<Obi?$wCwid6vSSbAR{o|((fBfSq(%B|MkPQfhU0P~H'
    'P@flsI0Q3Qjm1Hzozsqr&ka&Aj+~ZL0qj>)ZVQbxnQIskne@b0n)NGOd<@1xiee{Q_QGziY=Sp*r2Vu0c;%Dc$hKXb!%TIxtdv6c'
    'K{N-ci>DJUuG`MsB@aOyg;k+`dN%9XMMUryk_U%*?qN-PAq&qzWo?g@Cw{*8VR<PemYy$HI$nH3?xv_yv^|>K$HbvQe{-0Av8#9C'
    'MXQ(GCafuIl30pU>H<Shid39>tiaijp&7fG;{dxAsEhMUv1bGXrIff$8!;W9a1dGShWYMA<6zBA7-@s&N_$3@Isy_Cq$lZhN3phW'
    'U@dm)Pc#NQnLT_AUO|lJ0A+@3rRB-jki5{>_Nod3sbmRU5yZ7<jtYm|2k0E7+Gf+WNI<?N+cr26*dwePw2$wwPOkGm+6dZZ)72(y'
    '1%T_19WISS=cv%zM~i24O$dff{USMS3wBpe{os|-FIO#h*j5q>VDzeU&sV!98yELy>ERE+0(pGgmY)*f@;NAd13KH1SH<oger4+N'
    'pCx@`E9vK3KP}+FCXd_8RN5<5d+4ef0T)()aW^yKC3Teu(RmA`6GY+YrgRCEnBN{w=Sb>%IsV(CGV35)?+x1VIcSxzV7Y0!Js4(@'
    'o#&)ztj43Oi9&DR;b3Py$yBe-%5XDDk?rTV8$_ovijWXfU}+%Wz8-1Y+V@hT_boL?g9}d!+mWq3<?c(yLc*bw4JT*AR9bmsGZYfG'
    '?WM)OUbGLz;{p-WE1H6~#>-d$3+RK!hDM5%(*VBeAaL=i(69w5+!R}IO0T?RbwCV^R_@wjH9ge`84X>hg!?j=6T~9np*lnj+MMK7'
    'Xvq_+Wnx#^^4{g~q*M!g5fCyzxE)F5&p#l%PE1OG^gdH>Qy6}NgVjeIQV(P6z6Ly@St;$7|A{*6zHJ@m(1=I%InmxE*}<%6E^(Ou'
    '9HRN#)93f!o`_pIQ)50pWB^N_cb}eq(}Pyaos*8W7En}sYX+0U%OaEw#7*g;t8&bfb<&gMxhk6+uF2|}to~Mn9ot_s)iqOHGu2F)'
    'Dho6~$C)rwPA^NAU5)khLO!L{$%|f7+BKz>v42v_sX`oR<{Xt`=wCD0HIrR4+1~>05zl@;oagG7cd(&-oWXJ*nG=IENTy`2Qn)X<'
    '^WgQkTb)sxXTprDWLL?Tkj`~B)#ZNZ)nvMcHQ$9#_HwQKzdwKZ|AyC0{4Ji9k~r}SZkacE`Dc<hg}3tI?lAh`mytJf%l!Q3RlNW0'
    '<LCE>i~MQ75NC7lmwx}}ZubRa+~hhFUq1fhU*EqRKVhvaL3C<!@n#ucy~98A=a&-cFgV`iFW*0Y`tZk(zx?gHz-IpF{k@Q848Ol~'
    'H`ys7PqfDPfXq#NFWy@pzmd3%W)B@5!z((K`(C7_ObPp+o$2@g2>f0+J&x>4Cs(oOgZx+#zkNIPtjd3R;=3Ix)ylrx4cQ;eZGr=D'
    '&fxf};5w!p-B{Zl5;~J89ehEYGbjUvpz`6Lp3P0ME2MVkCb=Yk8>3?SMS1_l)4hDQ&Izo@km>YCIMHq?S4d~o`j4YLs<2-|_AU7g'
    'I~hw?osn|iN|ups{TWHVd!T-bmv44Oi3{B<<cTY;+UNTYshQ?AbHP<^Zn7-SQ`NOF(^F2xGn!V=p5HZx{O-^9haXG!6*}aQ;5+G&'
    'Ll$&M*Ox<bFW2{q<_GvFXPfbC(#fPK>0+p)y8EVrkr~b#{GYa&MFhXsL36Y4sZw43*zLyXBa(+YYql4D#GvTY&s_Z+_>mlvDf1XV'
    'x4_odkDw&f0_5IEFD@nN#Ofgt2mdIzlboLqEMz!N-TH=`o?!ijcr)Y-UlEA9H<n!3-H$3srT14D00ZUiY(bHdR(^#c5j+M=*1gD7'
    'm$MWq!ngJw-bg3vWX+b}UUSz`;mvpbRM$^+?d4bX-~aj#cN#inx-nztH!dy+QcYq9`%1FKrkcqH9KN9W$PTW72Dag~Dq8tT{+{9C'
    '75k7dohX%K+b0v2_@wyqWf`Eo-(7C(yp}ld7ZfxlVT~D}=M38s27PSV*+AeO$bH~cVNOAvVynQ7{ydZRU2Pd(WvMGl+N(f0i*X>U'
    'DQJF%?Fe<E$_J6UWFKyo-Gwkr5y`C>8cI%&IBG>clh^SabbD<{(zXXmFIVIU<<q08IENdMCPNC>1{n&9@shAKyAGjd9#!2oXN_2='
    'P)hx_7MB^tr3{XgcoTj=2e+r7RP*;;dUSqeZ!F2StG8G5_0ffi4n15syX~pmL<UiCrDZ+z*4ijc@(patE2I6}$R@3n)h}vulWC=J'
    'Dl>xlNwtN;N|#W)4oiNQbkCHsvBAr<d8vDEg*CYjr;P>exK}V8V<WX>&+CB+u+$WiR&s;41QXbOBgxwtUL$^l8XR2SDh8L+0}@!w'
    'W%ZJ9B8PIU$TAnZ%S@M=t|@8&+k94}92N)Pkk$xH@zTmN;#t>U%EZCsSJ_}Rf)21PFMFn0xYQBMGef^$^9;RYb5?2su9ffUm``43'
    'wJoQxv1;DLQ}Qr>QyE1n64-qTo01t_CErU5*67aoL?1p!WAe?eP})_$v8uWE7t1i|DV1bc`WiqT`H@sglCIAfiya2=N~BgzJ|WsI'
    'mS%Yg)P`pglsN)zCCh{B%`4cK;>mPGCtI;wm9%hD#b##zKpjSB(N7ji4WRE+L*%o|Y~v4a4W?$ANXEz#N(hk8K1-GozRnL{pT4x7'
    '5{0l&_iLh|mS{0d?oBY`hY?nRoyVai?<bcb&pKS3nU++E#xH%{guuz+gKspZYq8UNZt&J_Se84xg`S;?-ONdGrEK@vv}9xVOD@Z<'
    'Fa@FCV`Xzxm@ZhtQ`7l!>}W_Xh(_vCt?}s#*1+>WO%K<J%}#WRINj3!{oB{~`(Jinzy2GmNs>q?-J6>(*id$iLRqzk<!fH6;91mr'
    '@I9%ph;`DWf+RhA7Y*dGgZLu}T<A;=Z#uQ=6`y5q)Gx7}-Y+KOTcNt2!M&sVOiQdg)1In7S_Ak_t<N|8wM+A7NcEkDMrkdgC9yc2'
    '^>u$m{!1s;)#>TZr_D=EBMklg0h@c9?(HJO(&Zs=u%*yqZ}}Hq8)mUavE*?&l&-PIS912=6ihsR+SoJ}&f&67Ip1sMbt^8*$q5R&'
    'c*sAgkN4a;`GgG1)6>gsZ(I95gC%cfGLj=k5b&16cY5<yg5Mek9&SQE_T#J;i2105+a~`2T_A129F~b$-2^ap)0Ea#b^Se6{G_GA'
    'P-Ve-CP3U9ip*?9!~0*pfBf{}j~_4M+jo$VN51~p>~!IC{G2g(;gfXj*9G|+gJj8avr2@#Eq8@Xeb%Hfo7DDt=*Jc=!*iGS1S_Pz'
    'F?!nT;Cz%78C33@F{$Pf3|%Tn(6&{u>q9R4!NJ(U9qU$q`G-ZtjT~xWsXHrL>dQajL71KhQdQxsJAAWyLh8I-hTR&}JQ?C^3Gu)%'
    'uAsS(Sfc0?cQzKTWwjPv$!AtLUJJKKN9D_+GeyVPGfDFnOPV)LHr&A^Dff|67t~SUKqc-qwcy$JNpopz=687-`eV;i4SM!rt)?1Q'
    'xtksdJK4tcWM+qSur)Iq+aI~}j}}5an(L)7=%zjFGvY2+2(<+q?J&{kk7_1A>p6hW@BiHGzIc^b#qePMpXvile{(ApC^A5OrISsc'
    'bW&S*E~#W>bVw-^4+lWcL+?0vl~6rJ@byytb=^B21T$5ET?cOy|K2zP^^Ngl+6)YRs)YG(vDws?-sC-}INXxX-(yQw*@)C6nUoHW'
    'J6dj=od0s*>);B_yPyQ~PR;ft?bfcypd}Bu<m)R3xX4DGKVrabSXgP-NNV7{`NjyJ(&+Un$0Y-OxZsW;#Tu~#|5?C?ldpb5iXU9p'
    'C0?a-WrPluT0<47oD2sX>dD$&SyOeS?e)&n4L}mH!X91XH5!d|rqW&Nccqt~b<dU7js17)*cT&=zTXsJ?s1X+$>5LVDy?VN=kbiV'
    '`^8kabB6}K@&Q&vxvyW4q$o{pS-rNT%kH!>tbuIT9>A3Q%y*}Ba4m5juzi!O8n*nZGQs4Sp7A}Ti+o$$VQg{Pnk<n>2&sdS?P@*h'
    '7cvPJWzX%cd%^>#ug@Pp{p;EPzuA=FRTKZl(S{*=2crbp<9vGX>7IQ&L^*g{PAZb>2ER!oTW;RI6_5!3`VV)-a7zoox&YJZvL`pX'
    'JmsL2d4G}2nw<z9<BgaiVYd|j&Y{dXc?MC4Mx{u4j&iwgE1&*&*0oIV0~v}|5P^e!B$Mh<T?Cb&Eu?geSnkoj`Wf&#h{Ll-0Q#n9'
    'EmDKwK@(Nlf)?e~t;}590P#bspH2a4%2KbOEb>cm4c%FijO|ld2;MNMB43Y=A<aT(S^BApBKA5_uZXtM;8Vm-ZSQE?0v1DL^R@8k'
    ')41dt-^m-X?8va84+~yKDT|Wy!$J(ZKpq&0>aR!`CaGPWM5^xFZVNhhWd-UocZ46m`98~()vZd!xI|cg<K5-a6ZGVZ-3O}9ZM<=V'
    '+1q*7y`5;&6T$K`8M+aO)RjEZG+6F*#PBO+qn@&nn;ug{i`ehnm3B%gG78$gH7JtSI}z}p;Z}f52L^8*5{xsZi)I_S;4(<zqu?OD'
    'GN03SA*T^9Q_DwrPJV~xn%%Kz`Ip%V3=%}h!o@<IT#?FqDrOAwm1G5E7>6GZ<5rbK43n|g=Sdr%pt!6YMyh@JfSM!e##BL!me@6O'
    'GQ*%r<nquT!{N|sg+$i7hFz&_vZq~#57Ye-r~5%`hVUS28CZQ=vZ5YjZO2l+&@GNEJ2jLHSc>idZ*<WdS>K+bF>%6eQc5N1$R6t;'
    '9<J+~H38qD7HJt+Ly0sW_t_j0+>XkL{+8AjMsDppbRtL-0yIzLU?^5;IK$!+jyW95dkW}2R8^9YLQn0<;)Kz((95v2XQ?UlOiq`Y'
    'v)3n${H)G{yu6J30>xAzklFY_(a|u82%n|8=*}^bhDBQj13N<SEPW$8L1}hqAeV%r^!}Bkn9Gk}R4&Gfu61!tu9hIzt4?24;}|I<'
    'SoCp)SN_Sx33&QonC8=58BF=v#Ld*Pw}Q)p9Vky`liT86gFy%Hq%vD8(<H6HQ;pG%UF;@2zR9sLeemG$gV6&lT62%T5bb*9u!O$2'
    'h&@%Xe@MS_11O5*77;!Bl|%+AtnHYI8{AXoVUsEQ<LFlmCnz?=qAG3-N%!;a)6;JYJ^WH>k1#L%*}aadNFDzCRy4z5J^~u*apMc('
    ')}fyXzHUf1D2KR|MEzz&4=X9Y#C$Tgl&g)}dQy6j&kSJLC1J{1%f=LS^o%x6yo?p3sohrUCtR`oi|SpKtdi{-7fH4)IRKH2E|dI1'
    'v{0*sd;)SsEzLe_SxP-!3D9}az?x)N%rD<Re){mommgLCcaVZDJZ^JZbu!w`#*pM=(fQx6{g0=oFQ5@i;Ta}v4ij8kXr+^CCI#|B'
    'yQYsapQ8O-wSP<gU!wF8rB<wUz`k&^GQ^Gr0^qJwXW_FRbf!Ok`q#7n|G&n{Nc%2$=!pg9!f4NNk4sP`x?wFo><{mtFQX^in3IS3'
    'vnYT`59vuva8;;xXWIPR-ETgZA9|+WOkARnLz3A;hf+SM9hxPVSNM8DkmMPYK8Q_{WhQTtBE|<-A*Yj6oD3WquijV77D(zUUu3L{'
    '-&qj_MLNo(EanAskB1IkYY@C3ZkKQw|1&pPc0mB#Cl7~boZL4}M$&tofE)!ev+^-(h`AFkn{cGZCdNOCuMdAWOx;kSrsE3o**j7H'
    '^NzG-6gD-0QBg?i3JD<=Mquo?7W|@Ncubdw*T}?Q-uzqHP?7ym622G(qoDRRvj&%P#I_X$Uf6tUBwc73L?d@*x0g(AIEpFUR#tr$'
    'DUjIxFb0E>Ek0PdVIK647mDUGAQhVyZ_l+>pHk74z9oV(@EV;ON-7eE-(s$ASXn%xV9lCsSy(XW%1@<#a0NoaUV#dA&-^A&ds0Rs'
    'UK)<9LR5oAg3QhlaZwm(%{e_zbC*&{9A3U<sc__kk_<#LC$L&bXgmZ<i=ElmqKp_|h%_`f_AOANx_D9FIiLB|@uTiV_+g&;n__#2'
    'Y_@lBohCg;7*5H`6Jt{rNbXFrD(<_EURHA~L_;Xsd1NbzEI-DFtzjopO_<;V-&uDmU|TYTABCEEBm{do?7x&wh~xpj(6O;)*d=v2'
    '$Wn`R;3JDWdHau4s}^mON<U?IHzlPFrfTWt^7eW*L5o*PEZhtYUEM(^m8XsEGnB&0Dgcp$@rJF|=*}q!mE4BamJ@9t1~<5WsbS!~'
    'a1L}O@vX{qmLjRCoa|Kkvd+6oVl#C9;x~7Oc6Gg*0SchCgoI>ro9mCn-cqcXqV3wyX}N7ti_ern{TSIPN~r3I-arn!!U*jgG70xj'
    'PtP;@-QsU99sV8Cg%0laulp@Z<SbmU248)=XCJ-AhjNq`x^a^I>-xV)bCvaV7P(Q!>gi4C5WoKGHmbtho46fYOMX{LZI)fO!mZkH'
    'riz<+?<OQWjab&=Y7ykl=};av*iPjCr6gte59FET6JFvL!fp<erE9tMkjYQAjNLUyEt=1A)|>%Wl^a9q!U6>%$U!tLtWg1r%A^LA'
    '&O;vmRzX8muT6Ia5ybU?BtEGsNYAX@YsW_+7PUAbdT2GrreD>{$l<F-KNU-ol(S!^NH{|E71GOS;A4SMM=hDxh*U+V5ag>QV+i$^'
    'k_g)*4{hfCAC)e4IG8HN!be&9vD}wV_QCySVY%IpVq~29s;r50Ia$E(5caA(w$^3q#eBL$ki=20zSsCzokRD&yTa>V2ME8Td(FOl'
    '?BCR$swR|3YzL~^X3?;hLixS$Ag~LLPHj*)EsFOy9=mfr6TkS3RCchbMp&Z&(2|GBh0GoM39bt#X62xR>iw>*Q69?vGb)7(saNcG'
    'iM`73qzuKcpg{i_#;6TJ;XQN}(~61p%ma<fRR`%amJ#RvPI8U2HQECPXoxp&-<C(Fp*k{@wyfkboz0BY7FbQdAZ^XUk6o?+>BMuZ'
    'U_H1}Sg!Q%iBUATJ`439s@OiSLo~UTZ$oEq6s(T}0(^1xd{=|(FN<*r$KmXYCq$~U=c%3^H=)%HTkIPOFC%>DeCF-YYpN&ukTUIc'
    'I9FeX8ulm^PM$i@#QUxP2D>}hU4f?(^`O)ldd0%J06mU0@d6~(@n2t|;3&sfd*+yOJy<6WTQ0WbkZ6Y|^*SJShpD0#1=8%5w`i3i'
    'X=p4Ns5#_S5&({pDC2OIo19RiAwwN8YEDvJ?yjyC^ATop$XHlUGFbCLlo*39waN%XCy@7;s2<J{;Gj@HYr%6_<FANEcC5jk!2US8'
    '_)<x&(XLWj>1U<bEi1>7C5XX@B3fuDvY>CVKekldeWiy+CGWBWyxE|H6)aMa?Q68xzTzN7tu3Yg^&RqIY)R*S3>xzNx$0|L_Pc7|'
    'mWZX$wm6fKpoD|pQg{Vz%a!}o>pc+xC`_8oj=F{T(_dDE+HH9g2(7v7AB?;TU4#m1$iUXcp4c2!O#M!pgI2t9+W|SE*gz~otDKyO'
    'NPj&IhlUDzDsRv~V9SrTL>u&s=r_}o>zWH|oGI!O_CwGX1P;X!r+7<UEdkG~9g17%c2_r2i*6m8^5d)8?F?O}tY1|}KbJo8P!1<E'
    '2f@!|%Q6EQLtTgXB?DnRb$Z#e6?`8vH{me>HSJ)<de9+`PdP_vz8KEBBux%2A9OU`wD?5JvQ!9U8SvT$d2?(zLStF<mf{|sm(oLu'
    'rB4}TRt<KvlA<H0&!_7r>j-lW_6}O4D?Ds+Yuvzaf~y(ws=8pD+qP);>#r~V!`+ovHJ@G484ApO@o2(fF_6QC=$KO-?Y@>$r|!zT'
    '@$AQ5utbXa8~4-w&N>z=3(d`>ZT1a05_0U=1Up?UrbUt12VXal4TIRR7{$#6O{>WsLF_5BSO8xv98IHo#e>eCTsYWLitSmQ3E@Ur'
    'IP(0nN`v~THJ2!1FX+IC#>tU&h;EqW^L;phh1i6Sh+TcR_%tL}HLov{$c3G)q*{V`a(NORM;h$<s_Lz9awqd~U|p_7yn9LR+nM(='
    'wkct<rPOa{!CN*E&+7X?Lf)@aH|m@eTKzt@Ab))L_-lESrE8s}_5N;&S4(Yn1pwi2{0=x}%~?{hL0Tc7mywl(rJKaNwnN(3?iFN^'
    '#gOoYvbMNziH^P~bgC1(>ciKkFC@3*q6pE=U5o5?bMH@Yxe#{HK=w@wM9ZMQ5sKIW;@X2Yxy>exQWp3myWT8CkwtrxEU^@9IOVwz'
    'O(L+$1F8U4zj01sgPe*jHt|LwrQ%T_S?9pEj&$nrh1=m-;_ttI`}%(W%kJyfe?R-L52Apiz17)yp{%yj%Ua<?Jzs=Mk8k-`Ot&Pf'
    'YIM}t4Q0*=`Vl9S*<b0*i~Z?9Y3yN2ODjOsJJv~>6&FfDlHzz74R@tD4qdgpFdJdN)@)gZNr;{lM-j^|lk0?_inl9ZT-F0a7&8}@'
    'v!TgPa#3vwJvvH7kqYWhpdD`aXQ-eyD3Os3$5=@KH`u<V8$9@NTGqTlnSwLY>A=CHrRozlWZ1&Fe;&#W!X^Rbo5bu%RtO4QkWAXO'
    'S;$b<kcVQj_7Q*+b~c`gbS6N~ueAaUT?bd_Y+nK3$i)w<TyOF3o@MW)dGrEKd7?Fxm@3T$n$>9sn2a8Hp_wT51qRTU$Ulo!f6(10'
    '90F{mO_m@Ihp#GRNqE+A*J73*gHhedCU$C(e7=uIiVi8U>cZ-4J@`{K&y>}$VYNs6=6n6m>(A2@z1`b;`1BbK9-qO5WG>hgdbKwr'
    'n#|Ah4%~D^KQnr+N2^b%Wk^HUv-5ez(|`=?LS5zxKUANo>eWlMOenD&_u#>1)0B>6P^VEhOR7-(t6`8tv^qzG>F2CGJqHAq>q~RH'
    'sx*6~P5R?sdHeQl;)l)xe^bA9h9>j!*J?^^Ed`S<rOv&$O(_7NdIB&V3H!P}MF$!+1w5p`XmV|j!fwD*veLBpx(;3I@HxW}FHu85'
    '+GK0cxmX5YLp{5+#_Qm^c6zy`(nlk=No?$wgH^UmE8x0rn013*6<}mO*4|P1RoDHd(Ym>STPs$EzN#$@UF9>U&XA%FY6}Q!d>L4e'
    '6e3*w=7DT@D6F#O65#`Z3a|CD4?o*|y_=PR+DAF}O0A_UQbtm`!D%?FGe<2LU9i*f8B{)ep@K5s$uSYlXRhb4PRLWXvn*q8mK}}Q'
    'Z5#1G$sdN_l~*<n5egj?26j+%GetTnxsW(ho*<;)XtJt2sL=gtZG&Oo`24K0ugPcwx~ESLNa#v3zu<?iL>kD$I$`dBaA`Er-5LxL'
    '_w|JGFu>y?3uH@fw6zF&xnW6_yL#5p7(M<sD5cTem96HC+iSW9VQ2xcEowAnlGT<`zq72^GU01^f-}0M>N*~+atF%^LR&tT%|t8r'
    'kcAJf$hgVj9;oyqZL~j<J(d+koO1S5(R=r4)M+)R8Y#!>W>9D(pjnX>+9!LL3&7v%z-Ud>c0in}1Q47`FhbS)ILCNfJ<~4-Et%v9'
    'D*N4>#!I>6UvT#anL%jQ>ni3Se8{SXbWGRue`6cC=0*uJmdj!R<oCD|j`TM52Rbu_kt90qrx4RkJ#i=Q*^gKA^$Gc<Z%?1!e|sup'
    'u!Vo^^X}8rZ^REBGF-Cvb4Yhf{>~}i0~!0UmB+VZcSQf@hp$gxoP_k)-{-RyOLV=k0BVh=uLRhcu9}Mgi?*|<oAMYmp_E&Jmd3dZ'
    'w`sU0Dt*awYNUp)e*F=~GB<5c?MP{8*5jFj%|M9$>=^4?0;;Kuy^zyLHZsWOtz+V*6#TGa%5WmG4!Y$qxv==x<tV#G(0gyMZxU0q'
    'Z>opQ3$lv~X;g3mg;FV10&ozS$2oJ+SYBLUquc<P3y88@g+AUE>d&=;o~#x!ZQtqN)Ai0aEuccF1~7Uk=Jg|Bfr2m#jpi-MJ)s=d'
    'IyEg;vSY?JGE>vfYS*tft<L$HwwbO@q~9j1RcQLu4Sda7rZ-dZ39E3C=O+#^TSKm67hZb}yBvhml%4!bgKyV3#>b*&jj*<Zn_4Kn'
    'pl^Sry{qyOrtDVXsyu|%t9IB_TY|xLs@564s7<6lkttf^t^1s$`Y~H=7-np2SW6Djd!hOaIrEsv_D#@2+<Dv^CTkb6>NBRcx8C#<'
    '-MLZbiNX7}rno~%#%RC0OH<n5^`5h|Y#>i?XKqxIx|Qe`MUO5dirzuv^K~loA24t<f2dc=*Oi_@?_W@r0Sz&<Mj)>mEhHk{_Ynbw'
    '9RE08Lr!5l-PVnlyy}3=tmvI?iL|=CQj@P&UB1dkO}^|<Iuk$H;2KQbdI$U7yF|(}CyOwm^p5+fTmLMq1B(bFxb9k*x~4xisUOU<'
    'j5r|nltD@|x*ZPFq~NfV!ls1Mv*fgTLt`C@MW{90CrWrlc%5{hWA@IjqUpkeMOfIsxxy%xtYCPqqHidfm3$zNp)kNKJP_25FUhhd'
    '4K!Ji?J$mzCZ%b#lQna>G_X{<*yLI4opqJz`rO%O@Wg`&$PP-Jt757$>PTSyi?%OyRiYDsaPUwJCR7TKya*b=;cLF6ma0eZ)6C0W'
    '&8KzM^2%xqMYR@sl9kyyR?w9M6}-0R5d3H{uK-7(jUGazo41G0DW5!NeU9lp6&?D}n<_eIP|EdOgH+goN29>PjZBq&%ATOn{Fd!L'
    '>FP3A+X2`0l$lHOdJ4x`sq@BZnL5$kL9NJDy9)0Nrzb<{IY$rTerntFD2&dkcI60SSXKtbvQ5EiPsJ8#fl7WDmid@&ZIEC&XRQ~r'
    'bbja`J!JZtNN;Yx^LXu^*#bvsvd^1pv^i>+?v43P3F~;2<SXM@=5AAQDjAvAKEFLUC{u>BZ)%pow)DO%4C8p<%}7bTe5|>WO^2?k'
    '(UuyZnw=pmZK>*~mXnG;A$f@Hz)RgWTrNwEbnmJUxZwdAJ$RSO>Xq0~IIPpib=D)Y9E02_-IJD*L`QvE*XRCmv#ai!(9;Q)0h~C&'
    '3fq=GX?q3p&CmL)w<bh^p;_3!PO%^bKRMcHM`m3qEmL?@S?;2XFFFhH5y%H?HB!>LU(|#O%flGpqqxm&Cx9yB2?bT)u>epysP!w#'
    '!5nGKwCdp_MRQvNDd1UG1dfz%QrRlEB9ImlS3%l<S97wI6N}bJ&blO;4z31WKG!zUBOgOM)q6piQWp2Y1q&r#*Vi)C_d7?IZ!(V<'
    '8p+<qS=X{f8`_oenz6JU!fT4K&Zl64MGq7x3fj=EixV&E^_}V5fldn0h%}t&rHVwpp)6}Ui5~Rm0}y&d*A;BJHjgiY6lYZwPqFV?'
    'PtmGrsrARSIa1zBY&%NVHe2AQ_qLuhYhfcsbvW^sZyM4c{;78%^k+{c*v2B6_=YZ*DUKB?F+K*NTWieJZ0+Kfl7)c)b5POx96Hd7'
    '46dQbnli}!Fo#dLl{MBPMm!f28?Q@*Dwk&$RGN4Go_49m=WHgWc!S$WUQh9aO<y|vXAKPHrdO$Z<O!EZv1z%D%6tZ~bc2|0UY2*b'
    '5}waoRU|u9YMLpc_*S@TUOCLuk@?9vpabhVKZ#hv^-RHTVBO{15w#>7_VsW?Ycz~QXUGmqZVJ&#uu;e^%{At&<REEBLFgT4z{)tB'
    'vIQc`M}^qCzQ8Gq3j2bIm_<vL1uiO7K!xRO=Qj?s4^e0IY%6a)$aI584aqweP<CXHx~K+|$>r|81>U5rvTsm7^H9Y649y~^Rp(`J'
    'b6Z}{H6X?sVE6{`wG()v)EnjZHdK5<jM40cUZ1S0W7l*Ki5WHlX)z-^+aVLEpGd;9@M|oC=mz0T55@DD4<CQ+bWF{lcm@v(BPs&f'
    '_O8ie(bBg=hgO(NvGweG*_EUQhQX$ieYs8{yd$GFPP@6<ymUq~wBq)&^x<;dy7e3m$ofwEImxx2-?}_Z$pRzUhqZKk>Fk-06}n{H'
    '*DJ!ujwH!s-!hBlOp)WwlPHyD+p_V?>T_#P8FA9Ziy#-y9kwlUtk&uP#rBYs0Z+Lc{IO7;RUC-h7N#(su<JJ!TCS)|;o*Vp+H3~M'
    'vy^aPtnS-c1f3<wa-kJ1KhK5#u89DvWIMNIjgGPUZM@OE3c!`}Ids)>;fI~h9FHAb)Oy_38v{9rp9xWuc7E3b=C-c9tb~I_6-FR#'
    'H_Bqv7Jd%ytB=&`@OUX76JB8Px3t1t)a@=k&N{HW9YmQ}@^l?TR%b~S5rz%_mI1lt0Ug8bAlSCgK+{!lwWUh4LL4g2*LTn=h4!@*'
    'cy+TDPxS_$tkpYN?9~yxdZMV<k_sj^M(-_*v)9czavN)x`rA{r=-#u#%L48+R1qa^nznG)R}j_Xlzc4bGbgggwh$qQs+|WT<ba(l'
    '*!Nb6RcD=fKpt`*AhEO^SBUf7OacsYTdbocn%v?hXi-6-n2>Wp4mI8aDOJ%%K&v)XkW5gIH84kq;Z|rRM)L11qaUy(He9QPkDm9{'
    '#aa}MD)cQWVOyDH!}v7UvxEx9iF<h4+p;w~1F5kjH&UWf%{4T`g~%f4J_es&=<ZLxz8?+VXu#c8S9NH>saYTe{A&4uRVg;@!wl}p'
    '4VN5gs)d>>ip!jf@mi^K`*O|?JQkO4Rzm-WC{6XH<zN?*)X|UJ5{Ul0a%G4Gk`K4FD@At-vh+2D7L|%Mv2llU&J5T><a{;$yltZM'
    '1_{qed9CLl?w47IS1zik*Fw=k(GH58V=6EOeV8^b2N<F?3a=;_oOPLjR+oc);=Okre6Kt_(f&q#0;Mrh2J~Se^RGO(g#I_>P+x;%'
    'CW%9ou-6-i9e|3a7S}Ml6x<X|=?2!{^0||ntb;24`(#)zZ+>s4#vjMBQ~~UqMV`WGHI(qt0i{!?)#0Ec98O^<kP3pfeqT`f9V2C6'
    '>TuwYzju^@el})qW7om|?pmP#QfC*3EqZN5X>kEo^My-dx#m>kfx6H>JQx?mp=*XKB+c!$o=7rs^e5WKW!DHwK{oP0<oa!WX<jDl'
    '5m^gRVjG))@+FSDE|^N{$YYS!iJf?q$^dedEG(W};y?RSUWxHg^ekLFXQDn~Wr4Fw3zC-Y$HVXV@+-o}BCeHN@tHjqL_!Z{r0&ci'
    'nEkB~gU&j7V`W$lU9;vPQ8%9Xsdr7C;-|4KGxg8W(_)3y)Xjtcu%oLAP2^8gdzAJErzyzYseTjn2TIFYI-EU<6Y_Bwit|*oRO?Dx'
    'G{J<wFbSJROW>fIb_y#`bc+si(?d<Z4cy5{9h@>+by=wD=+zz-?9|xKWx#s8#Um9*hdM!LHe7#|E~a|hD_2mn{h@kE2?O2XYJEnp'
    '4DJju|0L3WD^d$8C45qUjdEhW;Dy=w73j(9+tOuJNjN|9U82F&O1xVme?%o+w~}s|>kl}LaAR*gdR5qcj0Ab9spUOAfRu()!Wk^t'
    'z_A~*`x~|9HztQzNah;|o2pXL?m8T(dfW2M)Pf-u<r%^|7kYO#c@kF8P>MlEcZ{+;WPl{nqwNW}Gx<%hmeB_XJE|Cky4|wao(UpQ'
    'y0OZ!vQ_DD$u6u*<Z3lrrcx80{ya1R6TmFKcn+DcN5#>j?5rRe%swbkT!nix3DY(-PSrM=)si`dwkp!yw3578c4l?>^JNpY(eRb-'
    '<>(?V#1>_d_HNa?;r>SN?M$8Nr}NZdNySPc78Hp;((l)&NzR;UZNonwvi1<dZ<QoM-6@uo!MKz}Z;E<n_wjX9PzJW}z`7QxTWhDB'
    '^xmoDIJ<>x(2aJ+Ij6F@-HId>d{ELl*->~IMP9_GSh&WD{8;SVn$?wwZbJJW&c}e7*JJ^mOT21DW_a#85|{=+09t0w;8Bs9oe3+Z'
    '+QBSa#W*0#b=ej4tO)DX+`OIBdDdWCzc&n)g?Rw&WGcw*2`R)m2$Lypufe6buYWQwp_?q+bdqG78&|Mveq`%kb{7gU#XkMY*vd7v'
    'adct`5mnJnsEt4@;Md+Imh_p0vRU~$SxOEb!34aBS9(#QFfRiPuBB0S^6;xWU$zZD1H6)CEThpkr`PnRyi+jCkQAjVyDf$<2$NXI'
    '$ys9>wl~SfOe+R6`v!_c!b{*qN2;$cCp2^us5PYqW`sJNUHf1}cGcbiXmNsqchFW}m6J+*PE(HSaMKCUSs!|C)tMg{ZQ0VJ#_$HZ'
    'sSjb8lbOX?=mG}C*^<k0#INh<we~FPq-oUvrqLZa&|oOjjMKQJ!9gf@TP2G}7%H0PG{g8fvL`deaW=)48Tbx!)R^o!McB6Fl|+Qt'
    '0uXX6M;K(2ae)UaTdL;x6D3|+Y!lLinXk#n4lc8YE#i=k=Bg73nDX9{=gNye$6OgrjxeR<+OQ11QIbX|94)hZXQ3#yB&P+)3@bU5'
    'GrXT@QAm3Xvm6O_siYsGi=W@+eC%8rIe3^pcH>eMfG{IUpl2UYsQ@6!`R~SH885!(>9zCD+Tth6L?y-z&DEvG@oTDq9Su$NjOB56'
    'Ks)$T%#GS%LQG!e6+P7kgH;J+<fxl}&()Z>{%(G5iHPNxT}QS8l@avlxNFpWJyRXLBY3rs^G?0g&IdIf&nWwyebTAsyn5AzBcI~K'
    '!{mJ_IlR`McC8F@p>QkAVQRq$zi$Fl>gL|ugzWu>Lu<Ekcy-L*Q2>Dje1g)@Hx+DwR}jkkdfg!d=ht!>Z$s5POrK{cxOVY_OohNy'
    'Y1E;-#}Z!F;<$UBPw2R_NQ1MfyWVj*H?`?0(s6#>w@z^mv&wpZKVp7^(A{$|5DOwA_Q_FNdH2rf6oyp7>S_s#u$PVt$rl|MKFaBz'
    'x{%zI7hY_$-*8GK_ql-(DJOy=J0(z0Ie0#X9-Tu?21xI6Bz!B!3c3^_J7};UZwK~c&wVgeniV+8D*5Qelnsx!v`uaFI0HWR;5z`@'
    'cN>EzM;*bYM`?*5CIIz<`1YOXHr6IE%Der{vgyriT^h$%K}WST$pOvZpewT?aLXrOrlxIGkx7cf!L*zz71o;OA21jz_e(F?{n0!v'
    '=jl|P#HX_NYJl%ndPy0`)3IWA$!O&was6gfe4wl``JHMZJ=WaGOsaahL9U@8Kq3Y7dpHVB%DryIQf@$qQ=T$R^An-UsNsa`b9Y#I'
    's;)cZ$PWWL`v$t7kaMkR=ypH#`R4R8Ju#X0uhOIjSB$~zXjt}blJ3P5>;J}A3ooj^bopS#%{tE;o}i*$X`st;j>u22_g^99egcwz'
    'ssnJI7TboOtNf=1r|XUKc@FnTA+_#-$Z;8UpF<6V(=YVg|E|^`I1Yeq;#a!x8)MD8TD6W%DYTx{E7{cMr%Fde^9<M^20#WGjY}0i'
    'Cvuj`f$*eSkf;}G?8icG3M2?H2Ni^XBO&n>aRkB9K)URDsIpq3h%9mp8o%bbk;QPb7fttNx@;L+S<z3S;*80DB(%4kfZrrqYxEN?'
    '*#F{@@$7x@yH#t;x<G%v5gB38Cbq~^<Hbw3*qklF8>?lbqfI$<29>{$@OvxTiAL(<+_Va=j~!x@`+6VEfyn0>O`QE(hq4=WQ6ZZ|'
    'aHXxZTCtPjS7#b%Qlbjg)E&+U8m=a4)|;uvL+_td!Qi!|Slz$S3(4)<#x`?)J4dUEe7Os|;mGUmH93go>TVS91Y`A9aM=W1>1>@7'
    'G{T%kcA8B|HsXVrpNW!`ECO-pWn?p=n4ny=zc_T9EeZ;#FE9-+UeGRn29x%<+*%MRo!i?B5`*|VfB5?JMYH9@ynh2LzP$&a!q+FY'
    'C7|mT9vOP*B>l0M=M2>|&}@Vve&&Xd`?=%phbBALsIZXeGIW%l@ASmht7Gn8q}z5T{Xaf3w#Sc|MSQ9Q_I6BkD77Q$U~!g$h2QO@'
    'EKy-?^CFlA5^(N!`0&2$nY`6_CZE~f0uZ??>2l<%A}s;bOm0_AZrV1yr~4NDz6?A3TrNd~GB!{iW%!YsSFmV9lk(U&y<SNcmC|vz'
    'Ja4<VaI(`sG8o8)5K3kOX>x4v#og6<xX@Z`?qZ?v%lD6;KK${Ir$}d;3_&&^6i#QU5kY-k5aJNbR5ca{p*B4`Dn2(z!8meSP6e=E'
    'QMoNN(&UR_L}bzvUuo8_FyJwG{wRu_Y}pGNv9bx?(2@4f`s0;PdL!F*HT^Qx)v{6w-3QSeq%NLLw770NbC)~>aTHdCTH)DTV;2#@'
    'Uq~Jt=DCM8?S(8n2bHxwR-X9z;)ms>kXU-YT<Li64Y`}5PSN&gavu|i2K~)p`o*r^Ko_lEa+|QGtVv=iPN@qFK`Byk>T&UALxyJT'
    'W{v~wR-i7<FU6h_5R_8lHf_Xoe8NFwaSG<U7mb58H({i`nJeuXS?UN#O!)uooy%@qN3yl&|5G&1SOc+m5jm8tf?Kd;3c8@sI0L``'
    'Tl_NGI40}DiXHi_Sdp7G>o!WoT{|NqBO}&DdXrvv6l)6y)?%mrMq{v(*}>P~6~t%`P-e(hTAq9j$qRjLuc{!BN|wMCL0pUGpm4}7'
    'K<6mcHk&R*0<xBD+u%rGkFajgKEA^`xz7J+BWRaRSDUaE0Iol_zcu!qqe5>VEuPUmAs9CGi{!K|*iAk4gI7vFU$xv|M@cAv(NCTF'
    'eYJbCadCf=9)1sOkcWr6@>>F2J_n_5KxbR>Q?aLqUzxi6XG!1KPI~$1rv*IN<Z*qTN_(Md4}Gdez=aiH+|G=6NqtI$=)4Bf38HXx'
    'Rk{UA%y0Lnb0qb>9RF=mnRSq@cLweF9JESUuv|4g9t^X{&T~>UR^!ptM4`9uaImwUWU5zZWw@E7$aeGF4Wd&SMM#J#urv^GSC6!9'
    '?RzQF`<9xc!G))V?a0=ia`z=;A>q);hLf{lDy@95843y8@zUa4FFJ?fae;{G6-_}~<7F&>1@wo;hDM5%(*VBeAaL=i&~OAP+!R}I'
    'N-w-*bwCV^R&Ls2H9ge`84X>hgu61A6T~9nzB)t=+MML4(2^%s%fvoq%X{a?lTt10ML@{>;C3XHKV3k0pO};Y>2s#urZD^q_I4j}'
    'N!^dF+ZynMW~a2<{zvMt+qQL>Ln9v5=R|vxWCydNxx``qbBN~ekDuRve<U91M2-1yp8+g=-hO)gLl0UlcTPIgT0l|ltr<)XFN;t%'
    '5I3cVK9yshtdpK3&sEvva7k8|Wc9Bi?AY#-sV<r7lBs6OR9T<_I?jZda(Y>^>~5^57xF2sPG0nq(k>~jjQx|^P8H%nGv}xjL;sS='
    'E}86-$^I2^k9hL+;XGHry@L(y!wi;NWKImuAeoZ+l)`<<od+-1-Rg|mJQHSICA&(#gmkX6sV?_LuO`zqtohC?+4H^f|Nj2w{~g{l'
    '@wa$VO5(^XxMtqu`L9Vn6yC~*yTj-YKaaebTjuAlSMmOjkDuS~Z}P|8LY&R1Z~FG{?e+`CxXE=UzI^=k_a9#le_^dFL3C<!_F)-c'
    'z5PG)_ezO$7#wf%mmeQLefaa|U;h3>U^9R4{+>xQhTq?*hwK!QM_OZiK;|aCXP>Q)-$-0Wvxkn3;T0Xreb3TTriA_LWcv1(!0(yc'
    '<H)&mbQgOT<mZm~<NLASs{EHn)@@&@R<>?eWPdPs2oAhCgX61$>zHzMV{Lax=uDz?@C9+spbQj(%7=e?HaEqokUE{4<dXbjjEd<O'
    '<^5;B?)h))oWP0<nT{{Qk#<YDLOQF~e;DOah5Zt;Z^<%jWh`BFM#`;~EF)d}Gm`xDK>ZZYKkSMU7kXI86IWcd&$kY#ndT*P!BuW<'
    'vMkP1)wM9wQ%=P*npV)B-zA59^XL2h#geT;ha3`oCp~h=f)45Wa!Bsw`d-oe03YRSGoDR4nG_{m43$)O-&8O%!+C@M(>Ak+;Ck&f'
    'Hw%ANs>>gH+!%dC@}o|g?S+40Q1s~~S3d`SB!^_m{EU|^u=VvLC<(Oyxi`{_OG!GhdPu~@KML+7=jQ_(8IDu8zTu`PSbrhj47tNs'
    '1fuSZB{z2Wt4dPo{S^klKzTb`P^6@lUtvfDuK|;FFEZ8TEQN~jt-Xg2(uq1*v*owf+;voV^IewevQ(E|epUbdpZ{>9p;M+CGj@LC'
    ';({R6BzCZ`Bu8wjnQXw}3!0DY;2LOP8(yoTm7nDA8GgLt91^AzrE+ZhWWo}k6f0kr0owcB<;Koyi35K@K~oaem;rjuupMF0$CjN9'
    '1m1z%2Tm2{6x1oU3f$<=Gil$|mhn}Vx}v1L3Y4=L2eO)i<|S-Ls1sE_h}0$faI5Slgkg$EZpF}0a(cu;EAolFj_0D=>qwHeJy3eN'
    'B1b5HJ*tYce*kGRq;PMLp`aKq2}`rf5NhU8)pc{$h;<63)NgC?F{8MY!I2Vg!Vl=+_7s$A{=Q4E&ado^CE0fM_KLnfx-ik9mn&zt'
    'J(ZitAPVlZtcTuO8-+=}flYa3w0|2pq?NMzMQv^}trSjWMle6Aws2VK5{lPh$?uZxnNl`3_%Ur>>fT#nO|HXfV?jIa6->w2NG&<@'
    'dSC)9HHD;=+~6(21a{v@@_L5Xh+m-w2bb51!R7RT1Qv5yy(OH;p&To+%*F0J)1{_siW<N+pA{*G#lbhEH3Cz-w6ctN()E`zaWMH+'
    'HW-bd18mF7o@o{?bp-Rw&~Mi~LoYd;m70KS<$F5jlb2a-%PDNEnm6&3Jj~xzMv;mHcAvtgWJXuX_mYA&x-&k}AD^Q!`DRxr?W*5c'
    ')!h4wWtjAoN-`{c4WN$vNGc^s*Jq5y4g+{4QmZDP5bYLAv%Caq!#fGe9D$CK<-zsl6`V`)WICdgtvIbpS~#g<Gjo2R4x_W^Ckv$p'
    '(D$h!^4Vp!@gHvure>N*#>f&%2#~*hmMkTFogcnFerY`=3Spma*F-}t(PEg~n_$L;5mten$Dt+fCzl~lI$WHXmQ;zxFMZvFz{&m('
    '-)KzNVz>9);H}-TEO&Pc{dOvLGdIPRvfXFXl8rqtxh=cG6oh_{mCaFMx?l-UP3Oz8t0B1|8mUXQ#-}gX15f`nJzOUaJJBuTcuW7='
    '_pk4FzihvL{SQ`?B#}_MH#c3dq3jrivT6^@*SuE2lc@LLds1N$>!e8qNqY7!8pvY@@kbK4(1{%0bZXTrKFi*yUt&9bUQEWfLUlib'
    'XGiy$mRNVDJyn0S2JqclpC0;am*&rq>N^dM(pp4IVsSd_>;8)T=WeX4)6<<#o0pnK82b4GHupB&+eL<@%R^xANTJ2v@-MtL%wmmV'
    '$<OIfy2gIKlC$@wVB+y&W7AkThs!$Ue6N|;t+*^FCn)IVA^)U4-gEclBQh+HkI#?2yV~~|EO|4NksL9CfVb?w)2p`<{MI<|a1;8n'
    'pLexD%ts~MHu)dW1=1GGVVRiKO#ovLO=(?K*WXjcPg*JrRTivg0>r(c$jnwWy#M9L$4?*r{P`lj{{RVj<m->kP8a@;ml=a+mZWRH'
    'F38syBukc?RU+hVxhrI9S(CzSQrqjHFI%_`Pkp>6SRu8>=xwiq^HEl0P<d{~q?$`Gbg3Xg+g8D@54r6J2V;9rtlRzN3yX>yIn=^Z'
    'Pgb<mmoMR7m>vmIRpG3=e6wdl>b_lu-5S(98RBaR@xU;ypt+A&qUaNMHWuz>wH95;GAkUfg-4{L@@3JPqHFAlq<M`c&8sE{?qHIX'
    '`^c#a>L_ra68D<g@a+4fximKOyF3m3q35jzz5B3MQw^)!O^<|~Y-4&dvqL)AnwgF5kKFx73n3oO^->sg(;oH-ahD5(+5(Ptm}vAz'
    'HIvJF3gGkY-`njMuM(>m9?bt!eSqm7ZlwZ62B@!evgwmfY75ULm5huIDP`i}0O)z>9S1)pR8JACUaG&Yd&h%drYf-O;A7(JjU!Os'
    '7;mP{z|hA^nEw`=O>OB--gAn}E$RF{wq=!#NKKMS>EO7d<+{oJF9*I3?$EpoN-*!#98c12?TQRq@_<XezH)$zY}EM!2Hb{)m3ED!'
    '2Hu-*jPNOqUaxXoGSG($o(NK`5j*go1$;R9?l+|P!F^rgRXSHj=uoLORFTTbaKNFStlgD0RY%%h?>yZABoQm@(Jfx1(O73H-KBn4'
    'dihz;Txs3d|Fn*+7-97NrT}w~i}X(he<XKlJ-a@SXT;qvrox>&H0YH-U`3Ss`VC2n(&V<)YfHN9NgKl&$WHA6Ou5f|cS;A>66XQi'
    'nq1Vd<)11OOpfUp-$J^`*To&i79U%aB@ziCbuhABtw;SvCc&cYy}fl$cmVbF`QxYGpZx!;O$lB#@oyY$7_xUTN{~Iwr+Z8HWbqK?'
    ';Jb2CkyJPMO&Zy9_4ciRMEK8txG9EPS^(Asm`;~HxzXh*2c^vWi)8lfMDQ4I#1sj;rTBLaWzNYnh(a_fMbdMW%Y9q<^x|3fGQkgI'
    'C|W@T4!TGt)uXxyDnVOF=@_xxqkZ)=;B^p(XO95%RnJ<a2E&6Us<Z_y%Bx$Mxwrx1hgLtG0@ReHUO`#pm*5(DvLqSXr?L=yU{XcC'
    '9vwrPh0e0|Qx!$*b)sGoZKJ`bh@Cp#(Y6IFhREh?;nk;c$v1wIH)7e5VMAXQyo^#7CFzHS7*2saFcQ^YkuXeBr#gvL-L*XybneOu'
    ')Mf4pKmPE2wkfMym5OnRu>Qt-%A+^v$v3+XRGm9`;|8<W^X_{)(WWPY<s})q5s1`<Jkc~*ZlqYc&4tiW|EUtFf9eWQF5f>yEZKBK'
    'zAxs)gi;5pK*@uJYetiXb=pwHFZ9>+E(sPQ)0^4HpD5mw9IwPaMV91o!)=fFG7Pa=vBtm0dD~eu36+${v5Jll7W?~v`voJU<X)};'
    '6;#@q`NP-8FCr@FE7<rslO+^ZSR%16JT2(zz!(j}+evJj=4ILs*qArP+S@51N#ALJqDffK1&atm_RvnVh40HHQBl@f@P1X{ryvEg'
    '`Uw_Po2&0d0?kDv6jxX^6xxsV6lm@%k?-Jmm`LG9S?{DI0qr}VBw|bxmPX-bwBFD)1zCCR<lVR{O`^jtB?Z=^i%qhb6oY}>j--2U'
    'hPjT^*P&&3mD_@Ol(+nd72E*H?aFonrgunj2v-VS8jQTPtk@;2RcMgB+FA5c7LD1TCClfj(&Q^f_Td~lIm0EcnoS_Cp&SlWu_=pq'
    '1go2E-Bml<=c_36I-(;sHFByMjEzm#0;&OLr<wQ7#e8A9PZbS<%Bx9(|F-f^E>5r02g5W=QvjpCb#5JH2m5O3*jvHJ$Xh0!+2nQJ'
    'B^Y$594fQ5vZt}M;w)`Kp{z)_OOfLs`7{N?Ka6fQ(duUW2ho9IEKl``3$$fKzj9Rji5v*)@c$AhjXyF_cpIxyMDA;`;A2<7PEJ|J'
    '5Mbd1#fF%&<9-Nr_`Ln}_{T!Gv{c$7Y~o&e)^WX_{ja|hIgm4pfQEXW2$y+u=xg#s&<x@@meU0z<-=FAxp9ECh$Ul7x!R~DJCkI$'
    'ia-=g!jv`fjA@cArXp4CpFABs&o~txEA<nuSpG%TUP^Y!-5NJZwk-*&Bk{Tr(~^S=cGS}BvzD#YQ~$k4@vnHt{PN@Drw@OA`C0Y<'
    '$h1xCuiHUM>p(`5f%-RwBp-{;|E~70kB?tK%ZtK0OxlJcxVO+sC)G>}<b`%kA7wseMKHzSSULNOtS)kI);eHccvu-?#{vOx*QryO'
    '{v39uKYsfC$^XCF0PVZrr6(4c3!^<2pcYh#Zdi*C`@<*b^XLgT=Hy}iBnn_T-}EFVxGU7BGi|f%?l+&x4?WXwCN5FPAt?<_hf+SM'
    'a}zZ64qs0Ql4eh&<6M(unaNwElDkBGJrgGbm&S|B(6SAZ`jjs+{BBK?eJXVikQ!JH&pqySOr~;pL0nMuJpN~Hvh0EYxJ_OTPk3f;'
    'nvA4{jsz6M%*w~CA?8lFZ8GlgFMQq4;_Jiz7^ZHhxyGP*{MbM5NLxl>Qv(<kh4z$?5Mp5j#;$8Q>CFBSPdLbA4*wcCBm-NVgfF6A'
    '>8NOZ!{Abm*zQDu7woHzr3)>CXynOKBu9g|!2)7sdJ1<Zt3F$KVhEK|2ZNC<J}eGH*j&GF8L$%y(y}^9Ypp(|qAPt%1ZChgx;2zk'
    'Bn@n`Y5`%h9nz>^lA%Tv)*{<#4`ES?<R~tR;1=qhHL%<vWhCOI;m9sTHCQCbY^m{2Ngo`ixl5@e4mXanR5)@&Nd_XB6Id-IG#=b;'
    'mzDO0O(P8rj$I3ss4iaAPtIpPb^NG%5q_Ab++zaXg3VIe{PzgMEm?VEY{~+`{bA?hzU$~^HP=EkgtDDSwvx#5V|>^eb|Te;2|lpS'
    'x?2I;k|F#k)XXCx*vnxvrS$3Cn*Gy~@3UptC3QK-QY+Z<3xyq7+{xR2q*}G;n9P;+(jIn&w82y@UEG9kvP00~l@bd#Lqk`0(MjcL'
    'WBUxHu(Aq3Bw@T^t2KIZ3PL4!V728$_qBdiewoxT@K!hnx{&x*Wjafd)KpG(Dt%e!Qzfw(I`{Ca8$-Lg-pv37&{{%5GP%w5M`CX&'
    'R!q@$ZRoVzwyDK;%AkIX>=q?d^+X>ahh1TWcJ`TsyT`|;8U1GQnoEa&`*fkbr~T)7ixN2t7p%coAD-C<Z}Gky<%J%cWdFMUFVb9P'
    'eVs)f)UkScQ#!=2U)@GknEMd7V{6HEmDFb0Z7V#g4R@-znfG==veSrVEv^<po}3QlVT0{N{$EN`hW|pINj~8%ZXxXEFj=~mTMwE1'
    'RLj_1bJU{wEO*TrU{$#>q%JH_Ac7o3!@?RBu&7LGK<PZ>^=}n4RQ29;R}ev54@lyZs)F>)+PzME6k<_}6QYM!a~%3rt&AMLYILbs'
    'lBAsdGDX4>s;`h<MgxllLLIeaUL#T!okEbWl8hnLUrHiulf1N<&wo_9*x_KR7z-a{>4$P(I@yBz%ffQIAH~QxwW_R%bU9hT?-2H?'
    'Jhs+l>%}bHK1kvqSKn%UtWKeO-(BGKuLFeN(Y<C@KK5^FPgN62B(?)pZL?_DOQHN;co5hHN2fL@oEF9V8?W8Do{3+4Mk+hlR3ofW'
    '0BFfW<wE9;^90w06SH#ALG^Ci)+i5U{~49Sh14r{U1F~?JSju*D=5%^hB0bGP<Rhr#k68#J@Y{0a@9fljAg{R*GaB%wnlrv01ff#'
    '?c4ImG*m~1(w3E6rn8xm+5)Qy7^JOP__50sAf0%w6|4tW3d@!LJu!*~*Jq*rLlxWSb%-X{@@?qsje_-YK!7i<o}OxO{beyO;W(Uq'
    '@q|cK_B7Sg<0iDaVT*l3;bnvmozA=+dQJ62A5x~h4(ICYP{SUj!pTzyns~qc-{5oyyDRWiq8^kwL$6p^7ogXXCSHJ~I{xb`6ddIk'
    'YtI~0t_SPHVavsq91`vDq+SQa?l4u<qClFx@)oT!Bn^!v12u>IlmvjIB+58k<t8W8Xvk0pjGCiVmz#@g#e9UB95NQxlML2;5GBT-'
    'ORX}(&<W%{B&vr~1UM+vPg?Mt*Z3>qksWHVC$K+`F1}P!YqYDBR{B{fcFW3fWC>z0qKFn6ifrg>?2j!KcVFqHQOUdP0B<%ZVFim6'
    '<oFuxwXZlxQEN-7e|?917~9ghFN21BfA9L5mi@Ncw<TgJbXT0oNKnGwcPYGr?#h+>)cZXV0VqtG&5pW__~JJ!LhZV|353>M_5~w9'
    'g>FIxHDuuEVsC7YDyIG<%|R<(x$S@)QEVU<p;b;!M5Mo-hC@RIy_GlUAF$;|TcQnmNA#QN$#u<zHO>@u3A+%q1%X3x#3|lVS4+V2'
    'YKP($dfe5G)S^enru_P<b~{72DeG6&(a)uiJe0%9%t7!o*|N+)#!%NGe#t->Po3WOYz5!P%uRSrKutSXu^x1Y<5SL2nlFa4E=iL^'
    '%Lg4zH!VKVvMdz>Sq8keLEao&j?h>Zy`{K^=cV+JV(C)`nN@=wt)%G4>GSFO$vVQEgS~?m=?V{<+#WYDoZxDP{8U{q&TU(?{q47B'
    '|KaAstD4WQ=mZ7kws<t*uo%c;Lv+lkj&@&5sZ%%Q-FSAf7i^JY{>JTe-?NU*%0hE9X`6jRj)WY$Ho;C8i)m3L_QBUpWWykKEk<#3'
    'LDOooM-cm!SuB7r77nISz2ZS<Pc9s6DaH1z&V+EIEF5|MS*1b!)S63_uorY-MC0VhIz%_j^7%d-!9r|8SH!NqTYMUltD4srN#w@P'
    'R#Gj&Jh?oHjw20reO2{VIJuMgIIu6*BHq0u_ifE*8QYXF*;49{v*05eh-dYEAR+J9sT*}l3a$PeTaZ6KeEhAv$<nn>(t3Zl#H*za'
    'y8?i4IDQA5vgRzQ*dVQt&&$Y4!qQFRQ`;eJZ1)N>$YMzNLRni}xI{-^6gt(3ed@#4$1fze<g5tM)lG}+c6IAdZ@Cb5&_H%g3q;GH'
    'z7dMp0pi+$Ho46vjZzl)B&XgiMUh2&lPs|mY&hk;5KSVm$^)tZR)26#VS}8CEjIB+A*JF`AX(?YwvKe_@rB#|UE+VfegFD?_sjO{'
    '*Z(~EulJ&Wq`lSId7-Sf(#u-mL_J@GO0RGES4_7gt7>%A*bQaQ3HlL7li5G%%!~c$Kxyn@N=qw1)H~KmniXeCL6YKl9u0S)I1YVk'
    'd0{rfeyusO43iK&DUKqRohR1`K^1RTz__djhA?I>DrZBJpX8$268h;V6-6qjKY@0*-JhX?+Mq;6HXLIm0o-8wmTvIi*J)Yv24xD)'
    'NT&k_la{Ja*pOih=l*#pHwc>qly4HVCs`pVa6vL@*JdF@Swmim$=XK%PT1ObCeoPzIltBlFmxSUp|gDjfFl<_ta81@zk8Omm*&w6'
    'IOU1fP-3by7id<e9bhtg;Du(Q*cTW;Un2i3R{cRwpKu7Ul{Q&|I2^vJkR{<+$4!e_ehfx+Bb(T%Me_MR9w|Dc#HtIcul3+h)jU&H'
    '!-mx!@tg1Uzpp<{PxNtb@8Q#TG<bXl7m~SPQ|Q%Rjc77I%{y?@5nX2VUXNCvQp=Eru4kw7jHdw^)`dFH6~3>&Q`M`NXqixAIqt!W'
    '&88_G$)HZ7ZkAM`_*cUqiD-3>2-DA5d3r7gEZ3Ljc2#NiNSpMB-}3hD+r$^01pcPJ?F3Ec`M1@S*jfrET}qvLahp;AK=lM*IuiC}'
    'e~K<NY6^Hrf6?UH9);b2w`8Sh@ns*n_Tf{8Azq?}g0#uepmVVdzJ_{sX^q#xW$*NIOQo+yZj;#9HwUY1msY@K-!S_I{ZxRF`B3{r'
    '<)6BoH;wkq8Qfa2GW11lVdzsnbLtE!+Mu?8u*R2x^++MY#cv+ShWo-QcU&U8Cs5(FUiRVNc3baeWuW#^&b?A=>57z*lx}bu&g#rj'
    '3q}|0bbJPt4_~OD%y)83MDv;JIjj@%l<h3b*qdcXBX-+HJW%qN;dkYgjYEV&2Zezh6x~dbPD(B$&XgwzDL9&}Di11jzgpX1*f%~u'
    'tL$qs+JNrqlLHdElFTpop(~LF@~}>rJ0M&dO?1}=L&RM@p*#%mILiXLBM;hI1ijp_q{>}AYiNvK{~MIj=;_K<bH?K}-GeZ+0N55a'
    'nlj01%c$R3R&1H@wLHNYJyLZYk5;*Z<piNEAIo8)m3zp-2Uld=<ZusE`jIv|AIToeiXu)qd#dQY`!wpbnp2IGV|6nqG!oFP$O`R~'
    'y~_pQZ*^d_CTcq%PE`U3P9+$j>V2GJd{;fwF9$7|<OnMJ-JHftx#VB)^aq(iXx8g0<{$i#RSoHwuIc}cZQz<4CCFGl77HN1$CYrT'
    'x2eC-nJJ7U(Q!A0m~QG9cjBJ?d^KMmk#G9``1$?!$1(<6_}e~jKRy0Ie9=C`CHp-4bhqU99P>Spu@75$d^=7@^lyIn`uN33NRRz}'
    'K5MZ=*E1WS)_D3tfSu`6a}i+Cb{6$e9)l*7ax2i%IF;cx4fjN)FL_Rl)X>$hzrtANrtPU6DGkkfJae!a2+^M%V|`0NHI=a!avI4-'
    '2HCuIOx%=$A685mPDIv0w;U!H7XP{&W!DIL@9p(XVv2T6^{{zCc5xw%3QnL<Dy2#Q4kGh7XD%AciwkU&8vt_wQI@OF$J;{vxm3`T'
    ')k3D@JN<pS-r1%FR4CN|MlZ#@egrH~5N4s#yd}9Ol*3x5ro~Ej%-BX|YWi92`t_#OJzvu{)76Re+hny0O-tRt*Q{lFGZmk(3Kw~Q'
    ';t;bn<T`fawb!uAK{!p>$-g!Dc8z0vENa#WYdg59h0+W9_E*}wDj#6Vt`)AzLs-3PhfTF57+j}no#BhxMEV<<qBY*S&q=Buv(<)S'
    '#>R%V<O01Ds?U%!kBMyG1TDm^$Gu^)b|I@iV`_WrO+V3-8)cptyl-oYJCtOM_Pe_@r43&1IZMk1@&q^LMkT3RiLNMmbs<so4jP}Y'
    'Q<-1Dz}5V|UMXK!dIr6JK~)Ac#Lyan{M2Y65$V2<2q@(E$MG6+3ghXvZoK5D_Q=eN-sv5YR_`v<<jbedf67NqKJQRE6F=GD8caQU'
    '2m9WeM9MQKi!h?}hWn~(|17KniwGmQZd;hTrWc#k59V1$91wfTASD^y4u@${aM(#<Q$p!ka$3Eiv5v$d)Ee#+CA=cMPCC#rduMmi'
    'bm74wEbMEpFp4EB7@n)>8%ky+AINJc3@{511hwN!vaCr1O;%((j3cB;X&UWh&0H=GY?UrHc@}$TU1hpHceWWk@n8b7gA(Ven5v9A'
    '5?KGD<4awY=ma1fJQRZomBJ%0f(CH-nlGuP>e2f&^Rid-X<fCvvKm8Ct%aUsWwwqLbR|IrukASm7cJ%$;3%}wONjLF_V797ljp3@'
    'F@2_@Lm&E3Mdu7kxt>dq3On#<6j->Csj^Sm6EvFNvfU?LT?T7A;JThNb7@{r;V>(8J~%B?C%QYR6}f6x;ho_0WGFqS=t109-8H=m'
    'qqC}QIf59Ll|iv=Q?S}ou|-;-k_*E!AJeT35-jJe^<tLJ_x+=XOkWe}&F!`xuiX<z;0R6jX;Y0hM-9`xF~2Ec9gmWHWjxE=V=8VX'
    'BlFs)j|T^3%5e5g%{I6zeJ%^bI39R2Qc}-fYc6Edp-<IlOAS!XP7s#vsOqPdlZyUA@)FyDmwMN5yDT-*y{W$7h6iNy;9V-KS7Jlq'
    'uudcQS&zta405A%Pg+V69rbBlpZmwnwz_LVPbXLgaN-6lY+L%I?G?;7KkKjFnh*tsW?}z2#ex+4<lvwknRTVKOyN;wxr;8o=`6%Y'
    'ARnyNNJ;B{Q4=aG4`YCj;x@OP0IG~96jXu70zm1Y)~_fBbEGlTu7|G_&20^&fM;D1I8wezWvkqZKw3mx1!)7`&B;<uELtPE>yl_X'
    'xEgf%T-!vCd<^YW?*(N_S=<K~Y?ORmU&~P6Z5>^{$vk3cBzqfYUCR+|XjjH-#?p2OuPMShpMnV%y-=ViXhXLyPQ0ksccya(Iw?RS'
    '(r}}fDiZmIvaIPOdeNgVK<E`+SFq*UJiZ80+*MIL#jbBXMXRQz_8-&cNO>=@?I>N_Y=NKN+j`Edg^d{1;lx|MX-I$gtKNmspFNde'
    '8;fM(2fAFQI98~{_!xw4tua%xwToLy76t;$K}G9x=|C$oxP~HY${_c{96sSz)>w-e@mx$Cye<){T%KJ}Y2NsI+NBzwvze6Q4Q?ZO'
    'J;f6?t#tU$8W_q=Kc()GCtM=MrsXy&^9jV#6=J@5Uf$tCcs}u|BH5u*(@YV?x58EP!eO3{%umh%9az`-NyHMaX9{)$>n`W6s3qaB'
    'tA`_6qhTC6Lv~nlQ;1fAjY4*5t}$;V2T3~$Lhm>OR>t9!Ef85gD8%0N1x{I1*cVL1ELyTGa8aQGDlBI^zj2s-h&rQZTY2k2rW-tJ'
    'NZzr4vLl1kMKzdAE_b&r@Fr!IeS`X$ha%=@XcjrGIxmB(>+*800WsD9!#9Ahoxl^N-Y9>zq2d!_jAk$N`eaodyQh0d%&-Yaiy7J4'
    'E}206L=v8btFa8C8-z367td!teEhA`H8q3c8N4ivs0d`+yC#oCOWzJ1T4655*1PX{SCSeS2AfKD<vNA%iHzDfZRcw9(izFnirdZ7'
    'hs$;A)^j-^>pSgol6yUWba|MP1xB*>Yw7sX*)tz2bji4@SA>sUNs`IFWfskuBFCF2Q7X+{%f>IO&#k>>#7P&=f?POvxNDJPwN?ix'
    'wuhVyc*^DAmxc1I;zHcEFop4iUDs4-xuPzGhX=N6vl$@oQo@0;x^HI@be15?g;uouJQx1ECIYOI?cA0%I>zd^@kaA102j*V(5IFQ'
    'KWug8c<kV!*5kI`7|22VOo*Da^Sd4}w{_)ZB^)fOFamMAQ5K`N@N;lqeWX^0$4mK`@C=K;r4{a?Zg=T*)`8vaAj-s&r|TH9I!mgE'
    'Fl_j{49G1H=ooGX!M1${ny!MYEmfKo;!ttEzJpdNw6C4OtDCiWsyFy#t=`FEua4l=6Gg?AR4}nI`fOpGy>8BtJ6OBa-=3;P_nsYI'
    '7I3GbiYRf_w1vCAf~X#+<YPIXxRE`yg$OxR?K~JE2kd0QxwlHJI_t~>@{s!giKXqhLY(hr5@3+qVjV5f<Q6wUiwX+Ggxm{qsPPs^'
    'sfsoNTD75qWP*CEfjK%1w?Zp1l7DX*{eUg8;aV+x^}MYv)}mlkp>IhE+sZ5(#;3WSB~&m@+{4@6maW+tNR1`AkrI_^uAvz&L>58M'
    'G5GdEcYpHr{b=w;1Ma%IszU=#%>pUlSIaM~O0j7lW^hLyxa3GvE!135T;^Pi*Giq+m2-aJvAF!O68b+xX{ygH2fL7@4!-1?K=j{~'
    'D?==he7LUNDY{#brLQTps8sBUjXRukX22FA=d1DOZ4;eWNO(@lYdr;VKhHY6a8X6Q7K#>%c2MjbQ-LYy{j_m8z!0rbctyeBtji3v'
    'yBzEj@3ZURd*$JY_BZMiD2<Uapbra~f91g?^uH;G`WhTFNgSetz1~3V08})!xQ5xK;HGFwH?aPe&z;<49aQn(C&POF@Ov{g{y3JU'
    '3Sj3f@)S<1p@fePD4ja34hJ3Ka0)|#R1mcF=YrDj7%2l&mjj3Vy`v2DvoUiAyAJ+$(*pgMy1O`R(Q7M8iwm%tFI*DKHMbfM)P?rp'
    '!MGp}T{B!EX>PCeM3RxCKhZueyGKw8vXKWO*Kg}f^D<eF$Xb9B+t>t@FLB*<!BkRL9)q+_?8c*129Tp<Ve#Y=|JfILCB{q9lW_6e'
    'iTZ?<1<oohNLscZ_t)|HD#F(yu9aJ{%pMCOp$9Wkcjgex{#J-VXB~a8GAxI#S#zJL8&7=IyQWU@)7X}o`se6vvBGNV>fV3Z(N%>e'
    '@~5diO8bM;6y)wyzlr(-rDZK0&K|`H`8W*4c`90}b)_wuV8Sa*!luy@IH;zb!palfqW#=-Uz2YGPcl*mr;Juz7OFaWwMPXzHMVmZ'
    'upS=qNX5~iPSBYR*MCYEQ@!n#E2!E2P(7!Ffu3-+KBE@~cZQgM6ls4aQVS|2d{Tdna$-H>h1vNP=*jDMrQ4{IaDL#sM1!l9c(+FW'
    'h)TL{CEYUDA8;7q#@=}JQ(^Zp66B?(miP1kQW{PPXRu@g$9~Q3Z`7JUm>gmunKckLRi&ccbvRJ<vE`Ym1w$&zGlWkr^yzH!B&?vJ'
    '6oZbQ7-f0L07;}r+Y@kS@`qq8qYn;tR51#5yJfLG6GWi&V3lKKtJ2|;Q&^YC)oQj(r6#=nd1wMAfLVO=>@#5xilYbFT|qLKy;q>P'
    '3eRQ|rfq1Ps%<o@C36aGRivkBC3&;#&g$^z%O+~0;Va$C(M4Q{Ey^P8-KuxP{f*wonL5)?=c&Vzij_nxC=!3B->;98+&R<QhJXLa'
    '+Diz3RFVjFr&v-3<5Cj6De9fw$JbFo8Q8)D`&y)Kt(|hxXQz_m>=v>?584^$oXX~QE0R#~hmzLGj>5|*@*=*)!ZlXp%VPJ|tgcM-'
    '5Zd){J_gjhCJX3X;#Dg$!*kb>z%&2?&@yudkBZdnOjt414rbXZ#sOKb%dVhjMOd%q>g}A)vj*Gxonf#n%mZjAQ$cP|NFmNam`rhd'
    '4KBrf{gZJC-DKgWlO)?*xq@BuC3pU9ccu_ioYSw2tz1(ZM<<35Q5Efk+6cq~e(g<SOP|;%o0adArR3ldOu(~vr8gA{^D@BTS{h|1'
    'FTc9`W!vyGz$;0{G8%nzdQET2I|Z{0Nl~h@+hX{PFo}hnoHeFldy{O;v|=!`Z=gsdyaZl!p!)iJLPIx!T2pFZMySKtwGT#QTkRcy'
    '7AGip2W|CLIjO|wH08JsH=O{T^`ZAxo%w;$mMuMM3?HDI`VfXWnOU5LE?`icEx9d6{JIWaYtN!inpO>98r_ux4Tdt!IE_mh9E5VW'
    'RkC=5p`vL{GmMWTdooj8XH#sMfpwUp#$@j)!nP%^BqGEXfRJN3!XTTB3p`NSQZ>h)DDl!_n~)~Vd`(7naG5=95r=FvSDi?}l(&vN'
    'S6=)%=E`VtgefJLhGp=Lk~Bi$Xqi1b3q`3VIW0hDSjnZF;r&F5LfT`P<w&qwCH*71`1zgB$Ih*hgNNy3H!ej12s5GtdiDn@6#yhT'
    '|J@iY<JoE+-#hQDEq=00RASuFTwQ7$zor`4(a=QiSRQu=w1Ypz+^8KU#N<_8(Nk?OSd~CV4!ZfbT#b3{@8;*Wh**x<b!97189}d('
    '+eXdT6V<^xf>--6@6=1}d{E=@jI!U^Upm#CSFgHo;8VPRnY=9}hu7NEu9ZP96mEq%Of4AUw@qM5-Q1g-kiFk<Xzf-Gua5aU3Lvn6'
    'Pf!~Arh+Z-3PO2TuRCPm{8~Q7+felm)2A5<u3h{fQz0-_8g(e|v4oekIPRY26FTlJ(%@|Bu6JC{O>KILbe!Jzty7%Ctg_zUkC@*e'
    'boU$##Da*3Ejdan@7@`m!jMW>T`ge|_R?`7`Jw~EM>+jd7m}Ou!i#P88*Yi@IX4g@<wQ{Aqy*|I2hYdQqjRXq0O?(hgm2|oL6;(A'
    '2MzY)?ZAHQc@CyZvjRt1B_F+*vf=TTwyBLCX26FYd<Wq8Ze#G|s3X|)C@m4h1fX6J-@X&w#@Yl%dAFA=o8HXUrE#nZI;y2f4ru-c'
    'U6~buTR!<RHEpYkOi~;UrsY(ru+}vHfWcU~UwX;ukLGDPPp9f8K9#*!1AMpAOUgi=jupF0Mk{BD>sOoN3uTST?^GM<q2@_uQq{{1'
    'at#du5-FfR!%=8b?sY4+asxt~@|Izmp9ob(4L4k$yTi&;b=@6Dei_i&H_-iroNG-(xBIE@H^;Z>k;%M&mnJp1Vhm<S!?JIabSIuz'
    '|2Mu`cv1DG%LglN)_LCW3o7cB2D&V#i2MY5{}od1Cm{K!Ism6>v2FOd%71Eby51;%&;A)Hq}JUNIWD8_v#)`0{Dq$S-_;rfhXHVx'
    '_?9mG##r;NR;^=G3auygN;b9msnQYAJOeg}0gypP<5Gpc6S+&}KzLFuNYo28_GKYA1rh|9g9<{xk&yU`ID+74AYFDnR9P)iL>4&)'
    'jbHQJ$YMCzi>CWLUABy^tmvmuamHjn5<1(Cz;6<*HToAWIRE02@#KB*r&Vjqx<G%v5gB38A-2d<<Jn6%+ng=I8>?lbqfI$<29<w~'
    '@OvvdiAL(<+_Va=j~!x@yLunZfyn0>O`QE(hq4=WQ6ZZ|aHXxZTCtPjS7#b%Qlbjg)E({!8m=a4)|;uvL+_td!Qi!|Slz$S3(1|^'
    '#x`^QI7h3Be7Os|;mGUmH93go>TVS91Y`A9@UaQH(%CvEXoNY7>@=H_Y{UmKKNBS>Sp?$HkCDxYVuEtf`Qp%VwkRl|zQ8oRctN}P'
    '2~67Ka%(}PbZ&1iNDSh2{_yqji{{9OdH)7he0vW-g|AQQNI>^3JTmmqN%~_iPZ_FbpxFpT{KNwx&vU~)4^4KgQDGs`W#}k9-|30%'
    'SI6AHNVn}o`hR#}Y>yu@oA_7<?CqH7Q0hd|!Qw0h3xC>4S)#()=2<WeB;efl@Zo*lGx<*AnSA1S3qa&9q|1>{6=?~eW^&tVa?@SI'
    'XS!|C@5`{mPvufXC}RWVQHCG6c?Fv`G%1gb)9aOFQ7IjV%ky3L7EX5hM+O7g5JJgJAWe=9zPP(u4;NaC&0Q=Me);k7(}zEQeT;Or'
    '$q-}%Lg93l8WGgz1tAW>OjToX5Ngx2gW_|86pSOc<x~Ls6_wjUBTc>-Mnon(@s(!%3IiU4=Z~V;$(Fsa5i6VE4IOF!tUq4)qz|&Y'
    'uBKn6x>{CBq30l)gVe>-krvl=XYP`RAdbSSP%Au}YwRK-_%q3a{XBQSrn8WR=b*B-hsqN#Z+=)_3W=qs+m((N-;ld0>J)8{CeJZ('
    'XwYj8(=WF52D)hVk~@SoWla)GaZFuc2uhKPQ;&-`8!|LwH*+0ej{<dZelGTmfS{BTx9K3J;}Z@di&HS)y=WY)xd|if&0J~E$Wli@'
    'VuJK0z3wR177nb%PW_F>U?;PKufZ#b(Hx-6kgc>l`5KZJ`r2MqK_HbZfh&Tz7R^E7kXwMxQL1e=U5W%`E!nogk-#2d-JpGZhjntD'
    '|ItR!E}O14VJiS!e{6qi>^nz=-acA9qkBRyZ0Z-uX<M+Hdg=$SlzzTyxxtQ-PynN!I`#W%_hjSZ{v<v89@roc4|nCa1h{+-O5cFa'
    'w&bT`PY=H`b@|VdzOkM3^3hKVc(BRi`aG5PLe(DnRE>ZOE5Nv&8S#?(lnBvz4Wtu9;pnP#3zV4O?oa1P>U%l<+oCe-AY1PY+VMGP'
    'm9SvBYI-~vW|5ueq-d<hqpOKRZ{OiyXFbVOug=PFGf9!{=C>O}r!tC=5K~}jAmFYZY1`WOQlj@QHAjOBPYc_Ttv%)LOU6RNp_2_K'
    'XTwxl`Cu~?61L-|#kpQ|4#ndF5z{N0g0{xXSO5#?4~-3t6e*_xeAPkV;!~mF2vWEyw&0Xrc**L37#OYGw8d(Asu408x=smqWiBU('
    'MZ$e`h#Isx$xoprPpp=Seae>i&W|UhTG)$#kom#wNGgB2fbc#sDFM>wOubEE_!sQ$KH`$PA6vII;0eu6X}A54)M2-6>oA8#JgU!$'
    '_9n>=W<_&}!~EwE&EFqCzyJP7Jkp68^Wi=NSo*yE^!SG!v|8?*bf~p}qS{+Cm>gafp==;-N)LT1$2?glJxQLcvdQ6+tS-swUq#rl'
    '-6d09GSwwh&6KIKKm&A~2{YyNvSiuaSWhqHQ(B$8=q06HQd$}NC$*g_#DQkcQ7MN0C6iq;*(H<xE8rgS<m<zEu6}z58`_5%EVsy<'
    '7@R>eCG#nT`;t2kUaq^<8MS#P%(zN+m3#^5TxU~V?u%YcrfXR9omsNyd*%QA{muV7yl3KX@uZZ*kymidyvg%llYA(=l@E7^(I0*u'
    'c{8`n&tI?N{U0Aczu({FkGq99n^WKP?cdw&7mRU}>r8z4`0MXKz8wC-T33ST)aLBNGQN8If9CI%66r8F-sCSoK7RV}=g+_V{fEG2'
    '{^0#RlV%LRzf%v{DI$-w#`u8DO?=NjTOYrXxQu2G9Ua3fI+pvMrKL;>``5|z?Jt4fGq=Z)bLr?V_AJQH9r4HaW4~4TFORI-zEZ7h'
    '-LA;~VD1nccyk8FR|VHG<><!R?vT)#MCsrQ;+#PlC<K)c|MYBbic=wVIycEB`NtR)(=W>V&wkzW-_|*S6&W%eUxXv=mU4x3R;~Xq'
    '%A*SVC1l@{W!TDCy6TLSTPs;cy7p%z`RRfBDV~4W6(uh8u#hLNxN4to9a1yROXh;B+}vbYoTsX5VWy{?if1&fpgq4!4*BNK_xp<_'
    'TZIleB=}Bx<d6j&()Hz#+{^X7qWJ+n%GqW-n{+ZMO1c;-sqVh1U}T2#2LGpRW)Z>l+G}nW{;E`$KlZpW`iSI5oiy7E|HPo^(@U;?'
    '4*W<C$&~pSFI!;i>qk%$Y5{U@q!*WxbYk_8h>L#|+)2*Q2R1Ssr*3`2O;51?LcAGrhpz}k-5X18?Cw{Uq|*B<41j_1cDA5MNh`m?'
    'kO*D_ChJ~gs>@jl72#WZ4<Doxb+Ts5Z?C!QsPN{yEY)SHF1`G!{`)`w;YLHJOgCoi{KmxvL8?jYU|&g&*i<vwfWsFwAKAe*(7-ml'
    'Rz)j6$=@^lc*Qv+Oead^*!IbUB|a%uzAOW@_q)rDo!1fv{(^$0B&;z5^qgTk!k~{WI~xeR1Gx{JD$FUUQ*0Hu(Vu71zN;<ct1NXz'
    'NqZG2XE6?BH3iK}*p5&qs(cWsOZMSb*-Z$;6p`GDp`qmTh=W$-6L}raMYq?HByD@3^m0XxQ2u&U6=(kd(qu^C-XKFkF<uguW|tw<'
    '%%iI7=ByFx6iTVz*5YGEaVdi%CEkP|(828~DAoLZmtLJ;*&9o;?dt6neSLIcqC+oN&Te}uH<3XU+-X@4y|p$9lY9f4^2%ucHgZTS'
    'W%Y~N++<oQoXU(~eo}4Wu+k+IufvkxCEYWnY;5pj+Pu`gx5AoShttM_cHAqNj<Jzia_05G1XyYcNh`U*TY?GfzLDhh46hNtLJbZs'
    'uN8yK=>Z8W=CXQAIFUm+R%Drr-Fc=<P1h7PfNef2QVxrQZ%Atdrg&*(8S$j+FJ<Cj@~dnx8bJrxmX|%#EL`dc=9!`2u6c%DayTnB'
    '0oTg+bj&9&v)YzZ*jP1h;wgEUzp0EO6$$J<g-ywfu9EL11#5I?e4;--M`QBMu29-lzp<*h_ZQ1B=_!?DSo#`39r=+|N|LV67>gYS'
    '@JggsO+F#oEtY0^3Dkyn5|lXt9VN?y>&+`Tm*UBEL?>HuT9veLQpING{6HN>XVFg<N)4dzQ$ysl%WUI6-Wp8JG?9#vC6o{#fBP(1'
    'O87cIe0}`VdP)?+KHaW~hFYS<Fu6Cuj0+>I0y~dGOWsc|L!NZFI591$5{+N_x(R`k{U5&3n6AZc@43NSyJ1=G?iTv(RP1JMiYsNi'
    '&!#0CdtP!|c7-Vj{T?fuqr!B-5}umQmt$8$azivymuihqU$6(B{%Lx+P8@ckTg35}{<rU6-|v3ee*O9%tR_h!p>%I<x?n@uF$!hX'
    '9+t0pt%4^}@4@$^!Xnm5lM0gb>|HdF#}49;Bygb<IlSrAs#koLy-~l!cKW=SjBkbNeg@Bu?lUd1?o4~C{%8&0yR|+&^w%!UpCQ$E'
    '8XBdwh?d0Sbk^7X75UHISXZZ~JD)Z$HH|Rz^9OA1ZMwIM3`>`Xz}}HUi@oJvcx{-)8pV>I)1h>Y{d^^7?@htP<Hg3Nv2YHTb;|i('
    'Gp}25Sx!z+(9J{sNqxNM?#V}FSRNmrAA5JT?=x8PW+o#!Vgvzi*?*^3ZzcGxap2)5^kqNqYJr%KO1N$EKcEYwEttbHF{_&Z#vYo|'
    'x~i_fr;4AnR2Zr(SkDBAdqa_#t!Q}v%a4zrKK%LfMSTAO67tB`ADf*n{2ebd2G1->*M41)uQ5oLEH|q}$lG#P$kehXh1sOG*F#^n'
    'a2uZbcu%lGYK_s`UI*u+tjM79+>A*zmtg2pL4vlef?XeS+Yb)L_MTX``^y&=6*qFIg{7XXXsa(@!o4s(5~QlaS$Fwn&xF){y9~QE'
    'sChEP*An7^VO&9TAF)KyC+=)4+{<b$x{_s9I9>~nNJr(%qBBL;*b_<f8cUj2O%B|_Bq{fiQy0`x;6NqrHMQZ{_epbUZ02`)8u~-e'
    'TMc^mVXdYbR=JxV2|L-w^kim-bg(ru8`~eb`;QhvJeupJFzBW|>=WWH7YMZl9PKdC=#Oe9m-Q6D=i9%x+b>=vRxv!7|EKx@(?8rw'
    '1&Rz%U+HAiC!N$5o=Ykj868r}#KQs5^UymEeoCmGB3Qjte_i*E2f<8LVAsLN#Mc`~puREQOq+qBkCib0EjF9l(wn^J6qj4l`Fm{3'
    'DjSiSB$Lv?aYxH_llxx|d>!1Oc^8ym-l;jBq}|#T8MNd9mwbKY02kS)^9KyL4GSyn8c7YjH{TfHQyRTq<+x;^4;MTUq*x<%;6Dra'
    'aPr-6Nb!UFy2Pt=u8h#3QfsIpm6PFsLp@o$D{HEbw7uSWx&cTcR@kFkyhfw3&Q!Wf{jT)#v!1!qy0QOh9a}NN==)6p<{lU6pA7y;'
    '?$Ua8eICz<yI)L&J9lW%D}TU>DEIXnk`$%MZL8OoblH<OhBc6#+5?z!pZV^T4z4B61GY7}sA0=LRVJ7m(=)z>bdj%%JB%$pwkAs?'
    '5<===WV>3A`i)G2McI3M>z?oc>g)5zPrpC;|5uw5ylUd#INC5|?_iW5dzer6mhQ>oA<Dsb<)k91Zt$BlvgPXSTLFpipZ{=E47aoZ'
    'tP3!mE_-sL%To?YnfDjT?AeLnG2VzN5_U`R?;OgUlV=cxXjF=%=O~x^w({x4v+iYrAIMO&f(RURkxZ&bbrDp8wvf^>V!22A>Sw^~'
    'AP&zS0qCoqwMY$y2TfFI3tE&{w=#2a1H=!lemVuHDNDVAvdAyNHS}ajGPX};A^5<gihMmfhBOPEW$ULZirDK!y&~F1gHI7Vb-bf('
    '3s?-1&DX-KPveqr{3LJ0vLnNWzAShdr7TL)4+}Az0(oF0s=p#(n50g15~;dtdo1YOl@+MV+!cQO;rnb;R<|k@;}T*0jrWvCZ_tx('
    'b|0uZckspyX0PYn_jaO9PXx<LGIS#lsSA0cX|UW#v2>dYp`#O_BUQJTYwi!RK{g%X>WhgiscXDmD$?H)q=F!ixy<}Ez4?HJAM|GS'
    'sUixaB&QZS{rA*UYPc?P75#8ecEv*alh|7eHHOH6gKo#g{yvZwR-`tJDv;*|M`;)24__a@h*+1af(fv&yAla{VWRgP?7~|?Y%And'
    '#}CMbH^oxYDP2T`Uif{veISXmVBH8T@&MUGTdfO-lCWa+ONl*z6qhO9p>K*v2Tjc<(bSQWs@$3n`$AW(p1Q+*mERrI1ryiVs8*e1'
    '+S7LGNq)gJVY!yNL)V65Ril$v+OF674!e}p4T~-|Nzzf=*mFCQ?sFODDpI?GmgQA$3+BPg@*`Go6C}5*srTNaDw8@7IHVngJ_bf+'
    'S5^)ZR`WB6LhTwUil|ZC`#Jo11~<8Qk!?bUDvg9PEiT6#9!;^qjd*g}6Jnhr$ma_(^k$=@{xtG(8H|nF$xYY{Xm^)8%*CEyx=$5N'
    'n98e3gG06QPcBZc(+9&eOH+V|zjbaMWi$M0>eySs$H<!@p4sGe-X$1xKp!fzwK8zAwBjsnLZR?RxJ!|v6Zus4!as~|HPQNC{0Gt5'
    'WGqkhi3_x4M89%W9f_PR>lgqMRE|F~P^28I<3sLiu_R(w>`zX6#t>lP1jUA!vg3Y;n)tl^^!Ud@Ke1HWBaGBude(78oBgl96M1wq'
    'i-3lDo(h+Fbm(jH{LKt_IhNCh0hp1f-`qHGU&NBJrCe>)lATGiTSb7AC1J|iT*l-@^u(m({>ih*^CVW`u~I+bisfHaxTR#5+^unw'
    '@CNZpDW%{>oR%b9u%nh{pS5hIo(kzj@_NNP=9eEIKYjS~%g?I+N2YCBf87p>J_j<Aj6t$7B>7l${&%&1eSG`^nnD!bVbVqw!M%l6'
    'I;mz-ATP9Q`Y7`$t7j<&$I6LZWOb2yv(^Fo!o$iCI~E9lyH1_L7U!@t{qfW9PyYYa258>}FFmoqTo~=K0JWe>bi-PF*dIPYpGQx)'
    'F((i6Cs6<^^QI>;!Cj#~ooORtcfa{me(0HgGjWMR4ud@x@|cfXDyD-vH$hYH@b!csX@^95vNcJTnY=}cvP-1XGjTF-X}tLGEZZQd'
    'Px&Il?`JgGr&9L-sm0^)+(W4MTMjRXE7YII|IAI6T@V1b$;;shSLscYk+jfAfP$D=`It4t+zGc$#y|aqulreiefS^4)D88-7_?U('
    '`{x~L%P4GW0HdN%1rriNER4X|buFjD*+1e5<Co0gUn7TPV2hLRMbu3kRl{!>T*?vKoha~veYLT4p=A(_Jekf@K|3r|OyTZi)n_ZS'
    '4WUx%U@)@9hs9|Ko9p*219n0|T2?1%t<|Sgbfs^JpbWf5w}z66q=EBREg)>RLmCxKGSrB|T4Y=8B`ivj9K}Tu+(O;62JStij6}RN'
    '9NC4a28#rlE%gv8>4W1mcPW*`;l@#x3P)}z$v`A?0;`3D#sg`!BP<QdhyjL3LxW@20wt=87xk0#nNJ-*>RyB&<|+4>fVW_?ls5l8'
    '!f;Dg-WZ#*Kya(s`MB>odRfi25DlSh=aH=>viukywuYTZHDQ7eth4S`z_w%vKMFPTNC@_F*i0#XI=5#3wB-A28Foos4zkn=w){e2'
    'M;3ST_8+NMEjlK1WxceAT_J5SRZAB);hXFbw0Nb&!p+do)m?N_dD_@MLn*AR0uV_UZ`f*$o}7YE$sJg2InjNsUzJ}bH4MBJ&Veo@'
    'zEzpdQY1B%lbuRm*7;OPY=+J~{OZQguC8}8KmoLtkdRDnbN!LnTZ$D^v|SrIEw^oI@trcLA0xX(2~|DO2gqSp7@?hgCgJY!@o7fC'
    'S-j@b;om-8XzywNdETN#&cX$2@YRQB_Q6}cFGqQy2PfITuK$ZPS6N?Ykq33Gp5BxW@#|N&Q5EJs#O>Hxa$P00S$5kBk7~o6DsJYz'
    'osjG_Vp)r;MUW?_LwVR>JCXmFl9b`UkY|!lc#B&IyE#mjuI1K4CO_3OcGn!WXg<qba|T#dZVagl3lxYT2hp&wMg=S?lNwMu4|)At'
    '1r1fbH{BIP5Z42e_@t^JJ+pSN6CZ_G)Z&Ebq17CRepM?Yhp!r4DwZTEXTMC5aD?hBq?ggaVu4UcEt%JdR7Ix{<f|lO2=$ke2-_qt'
    'ZRYbIl`eKTm@3A?2U+@|+?P(a;Qq3(-0nv)GES{3Ya(4v7VtZSy(*8bb=i6`OScb_ILOtv8Xv1u=-zi1c>U`D;dgYe*_Ds|o7z*='
    'gc6DEKvml;8un5szZV_^cEQo94GO14@&3kZcdlpR7oU;J4mQ;YYZL%l@=&>ux#K*+b>YOU9CT2<+qN~zL)m{urEnqjid~o3s|-)d'
    'Q2YuC^q*mj+7J}pLsv1am{`v|(70T6kUnD>aqe}JYn-jo9xy;dyn6e#JTeW{k)gC@C70=JW~8>jY61pnYZiX&as@~yo@)i`!Ii>t'
    'rGHP1qQUi9sQ*yK_IVwm$+dhNI(wsFeH;+ri>s%n8eD%_j7vBUXJ0%aQk6YT_4K$2t!~(2-%xlN;X|i0Z--t}J<*4hX|Kb%`a0CG'
    'N2ze~)PW}6Z~r$q-NEh(Je8;irOwbR7S;vmb)<<GAgPZ3`U(X{ImX&E$CT^AI&s)?u_cE@J3Oh^0kJzw6}2dkX0N<Os|-m)W640x'
    'AwMMn;3$bQ4p+I!2{jrr)B&UBDAncW;#x5uVJ3%+h4mzZH6KKYG3ZjOj4*Tpc@K%|;S>Q53iXo~Jm)q3ig;v)8te(|kE4q(mDC#T'
    'Dy5ZvR*K!SavWKL7>p>Qg@z&<`WpLVOU2z+dTCVhE<3=R4N6$SA_Y0VMtkim4pP+GQtDsdAs@!JbneTbA>ZG-zNTfrt@dq+SPI=0'
    'XEG9$u=iaGub{hf<v#U(PecF;lV-D{ZX>?<&5BUFE^h*%HJ5$C$WNi0P(ckDIJ(#yo1==UKS^`YidSwsAV(A%h(&0XlM@l?uczVA'
    'P(g3y4f+Rc`O%hWgWeJSW_og6b774$MP0%!1Z_d!P#kfJx75`V@VwfgxP=~fbtARt(XlDNzN+2M&~3{4Rdw`p=_3#2a58fc{7kki'
    'GmtUVb%<Xw5XMudw>?|I_c3!5UK3E$4pyuO9pd<ubCl+b;jBy2<k0d#N7GG<PqZvcg+P`8uWgVw$Ce{BmPKzV?%{bUJ)~IrltE_I'
    'U`Hz{I&%7ax_+{bFy~<JphddE!zQ=K4Gbr^njt?`7mRb;7Hxm~?b(00x$vsyvnx75fw?UnO*kwDa@Y_ZbE>1=*HY@#O?fw-UF-#0'
    'q?o^PJKguJW3#f*+)UbL-;g6A$F5DV)5T(16p4NCbrabzh+T_O++5JKn(Pt8eq|O5;ERQWX;iOx(Akp<2U|+9J*zVz+$al2o_|(p'
    'P(QWi5+&>f9T?F#IkFDX4YPc{4@a;No6r@ptM3+{hUBW|^+gi7v9py_OE6C^Pom>UgI!-$y%kRGWIhh;%e9DiFUfsd^I66=B}}%I'
    '`r|D4$OhtBeIH23`*rF@osvSUKgSm2j}ISzD{r!Nt&_Cg-!1WKsl%=SARLb00jI1vODZ-<E9CPsvXZcLllatjNE_R|f()`4624H@'
    '78fqj(HDhIbz-0T@b&Qv$t^i6LUeW0BD-DP`qNu3gdH@HUDE>5GN^BaB6fhdcA!mevq__r1wP5CH%n1u(cUCWECm}*c`rnh2(0pe'
    'DuC4=oKx5!r(%muyirK0coaz1Ik2rGoqBxXwttuSpKss4zTf?_{rdGkPyXw@C?IKXb#`7TtF831Rya}57opPYTmBW(Ey=1H9W{1C'
    'nR9}E#L;B-Pdf8re>zYadzjMF3J~><b&_VqnNpCXIG#ttT_}!2pITm+jj&&9jx56@L{EyNh-K%=bwW_Z+Z8Y_>wzJRnTyKV(Bvn%'
    'sJ4WDI!Z;63hGaw9d7q$sGv3|k&z9@SV;gk*uJG3Jot55*1SQPf-}<Tz`>-Y>Jv6(*uuGg9?A{ECIRJ}#Oz5{2nt+~Oxm?s$WYdh'
    'mtwN^5r7l6HlB%eCP2=wwE_%X2UqB9Ujg9A#Sg1oZ}IP*<?N+-^a4(KqBWG5D$NC&)oBNqj2?KQnJD%J2GEztKZ{j=(9<Uz0&JyC'
    'mLLv?uPS6oc-C>#VwN9+QQgQUc50D)zK=(W4k@wf!s=^1_)|5{l-00dwMYEsd;Rb0Pty~9+}nHj^c@WzpTUJ>F4z=$wO1pW%un+U'
    '+;l{j8NJt|)u+@lq@nBC={)0UK!$ap&U1zDtM63x>Lpqxlvs{?@M5!RN=GuN)2N#zRVe<|Fi0X=og>2Zb5@?73j)jarMX>Inmy7c'
    '{o%K~efu`?MJIv3sc$<$lX?DaH6^x|f=QQBr(WEq6aY{?0ho@2ec7L)3yqor9@1Ylxwc1PH{dN<X<B^Qhpv72lwpXMsG%Tjax~~%'
    'EQ7D1o?Tkwb#U1`z1&jitC8CzHulZID%+(MaM?G^zCk|~U}QejK2iCnF6T|7eRBr4R;&ztQCk@Ll+T<xLy9)2Eg-D%Wnev0h;Z?n'
    '2eRS5u*w~m2=570c&(Rx__y8GyIC2ieUx*r)LObCWhA8=oQAVHbJT*-1v?#|LFL02Dk$@v923!e=6Vk6ggj+C%QE(6+0lsIwh<4M'
    '{AKuEd1d1eq0m8LU<XAvQ>2rU3yCx32|@~vCacPW3f-^PHW>De&(A9Rnv6D}d-~*ngsvp>3x4QIq=7uF6Xp&GmqruawZRZ^S5GJp'
    '13b>MK<>zcwiZDzH!P`gSI-(6qu2iir8IiFvelgNcun^p3@re*MUAFRvf480ca{}fCVVYVa7K?*UB{zU?qE4VXv@cPm}uo5vhcwb'
    '88<oH1C@THjm}51$Fib`Q_h|$dhb4sI<4kZBjs4#3<`||G%K<~`(*EO0r*=T7_Eug4v15g0D@BqMyPrp=NR8r&-BYdOC~vj%6>Pe'
    '@lr1N7d-tzW)Pb7x{CP+e`HldI;Ly-e`6cC=0*uJmXE~($nS9_9O-T9FLY)KBT01JO(CY6`o*2NXFp%f*GJ@=zCV6`|NXIy!503u'
    '&)ZLre-K}^&v3~;&pzEP`8~&c4`l4aRvzDu(-HlfAHF_*aT3yFf1l4<EYbDM2B<Zjz7Sw%`qW$mShSr*J(S0w38mZ$v@}j-xJ|=7'
    'QRz#bQzJEW_3N)NmbqzrYDY>#vmVbJYz9K~XUACI5>QQL?1h|0vXMbHZyggirQnAZQ-%|fb<iz`$%VzgE=Solg5G<3eUq4?T~j@5'
    'UXWc}NTY%iD3nU65`crqJkFVm#`59<8|4PTTtJlND)jNTP=78J^klV=>G)26pRRYdX#o{VHGt7eF|Qv13lxM|Xf$t0?g{0v)~RW+'
    'k{vU)k(ru)R=a+^X?4%nw9RyNBK<a5twPgMH}ExUnchsrC#=Fn-k&(cYz?`N-FWRa>~auJQ+D!i4ZdCD7$1w8HNx5sZfc?Qg1-Hg'
    '_O8kYn6hhytMU+5ui9Z#Z3za~saj|FqBfEKMy6<ux9)S2>c?!gVVJS8VJ*2p?}X|z<ji9t+c!ZAaqDq!n5<pMs?V6(-g?td^yEgF'
    'CkF4^n&J*68KeE~E=_5J*L%*=vVlCojk!@t>Q<sFie6nv6upDS=j&AF7cg)&zpq!y*Oi_@?_W@r0Sz&<Mj$^mT1Z5??;`>VIsS3H'
    'hMdB9x~&^8`KdiJv!Zu;N2Jxe3pM%jsq>%mQIpR*l+MIYHn;{;kKVz)_a>3@%*i5*D81pn>e@dG>%bzy2(H@}rmpG5CiR1PmJtWU'
    'o-#;DMz_OZniL#%QrMJGdX}74Z)mI|u?V$>`$P$^2(Ob4bj;q_T{K;Ium}tLnk$TA$qI(&D*A?!S;+_T8VUo<!UI9=_>wGZ(m<0H'
    '*$(3fX;PX-J6SWAO9NY_i%p)z-dR_fuFsuq22VVgfb5{exhkeAqmBgDzv%c<S0y?D2nP?vU_zzv$cvx>9KPmDYN>kkKFz%B)qGl4'
    'Ew8M`P*iK7Cs~=TV+CDFP{C_^4#7o>c?CEMZS)c%J-j`9PWj|H>vK$>sp!y$K2*^;gHo>N5~RWoJQ@WSZe*(LQ}zUn=C^G3NmrM_'
    '+77s`r_5ZM*HbvmN}Uf*%hZYP4r)cN+EsWbI6WCk&nbEk_f>aIufpi8YFmyVhGk_?EZY>U_Ec<<7O3RHu*}DFYl8&KIcvR`rSpCN'
    '=pobBM0#_(t;cKk#1S|`lYQD$qs>vnbZ^XWN?6CEBwrcNGWVE@Tgk}0_UYrnL76g~eN(dy?n<A_!Z3~p-i(yg^VgaS*>vbrHQG`G'
    'RI?L=r8}znspX`izmUAdcHpJnHQX*sjdX9SFSy|W89jKH%IcNaP&lm9$bHr$vK)ilDBY8ml0-*+TG!|PakH)Nn$Xh;mI0i&!3x`!'
    'K52Ue^UcrttG6aZfuUL0zfQ3r1wT1BXh&vUDJ@fYR9Wt#i*Gs$@e#-eYc*2Rx?j|U3d_S7;G?+BZ6|;#;|T>-;IRNuI;iz4%E26I'
    '%(Uy_D@Ai#11aEHR|JlfZ&KMRw<3@h5m!OlfOm7UloN~ANbb5Mnhvf8T|U<~(IX#2JJowZnNk+_!37&7U)R?%)OTA)mv1tU7#hjm'
    '##z^LL>t<b@tU!;9l~phu+FDof<-SBC<@xpt&0;c>h+!J+<{IC(1<kL=%tE8zM(8@I*DHN=nD{fMb{N<xi*h4f)saE6i>11TTjud'
    'X{r6kv^i4VOKdwz*EU<=r}ws=GizZZMs+yxmTwx;AO5O$A@pZYCD_IynfQS&mnn`FDlt9=p<8Rr)NJkImXd{m0CP~$`dm8DiVUuy'
    '$eJ?9{V<15xRo{5B1SwH69=zLgesS37gU-z{+@QJ#^-D%rFeteNM29zgiR|Q{<8*#a??+#d*lh1NU>?Tjmmriv2=x)Z=RQTxDcLC'
    'e5y!xsMIu5MDeX~)x2<+rz7)|b3g~yb$$}DgzK4t-N3rbxhrZ(IPB`-h}LKrht7~4mfRGgm0+WgU7BmmTggGvj)KrT&VZG1IAse&'
    'mJbTCcYT3V78Ujd6ETaHEDKyzsDKK~+0JhqW*?%?=-F1@dXVV`j~bG9ETHVjAazj<CX>tEZ410fS!Lg#e&(Tw`5Br;POHw#;Oe@('
    'oNGXgHNfx<;A<!FM5#B*pKYl4gczgQ3%x#BRmbk>9uhNb0@7kewzf+qP(P7`XW?orgXjj~O!vj}nGYX->vT=cpm+u^3nMB5+4io<'
    'W6{#LLx)zFOR@Ftd)}3#28O|=l3lq@A$%gEHcs2Q+Pri|GPL4$v-II|-MaN$4#@gWyPV`+&mUbLreuMU?EP9gzI67?#|m9C?&=lc'
    'V^@-7vTvD1bEe4g=1G)FbJw!*%j$D$Zy9mY#j_w6&K>Sr<XElM0gCM*Cj*{xIrwFvJgc}6w=GOzJYm;06<V&SOX1;x?b>Vx$h(wq'
    'V65)jSp=OW$a0|-EkDnN|E`Gut7JR3WsQ!p`fa??yb8dD@;UUW<-!kJojD#mxTy8Gtv3d85I+;5Chh#L2h43<d07buiz<vj+-{V`'
    's4e^)+*co|)#33{J|;ZF;%{k%yQte;dYyG(cRPqOvE=DGhOEw#Dk2OU{w@P@%L6)w+d;5xpMj>U;A%^iW`#IZoUiYoRSNBEC-CZK'
    'EuQKPK3S`Gve>I5c=be4u_YBuY>Ylz7-z4WbL0-zF7>ykYSF!ChnEH1X{aJfTs3XsuCE}f$0_+(&L?hU4{aer4plo3M#up>S#a*H'
    '606QS^ME|$K0sn=JFXDtyO{(S<hEExOEkH~P0*r(LNOutf*fkR1yZV_jeu5ds34i39&2EZ4#Ta`N{r;+TSh-%OKiAS3tv5NtBbWL'
    '7**(7Qo^<}%ZBl3u4f4qj1%|pwzp+#b_P;oNp7S>rJ8GKh6|BJ&~psFz0lpCe0@I}ywQNWuCD6PfK#(T3i#FX3#(FW+J_n3kq0h0'
    '(o_pIR}_~y7vr^3=XT|sA9yS-KdglQ4^f)xbIZXlB&mZhxh4?(H|5F@3nU+|Yj=w77G&vb3N0!Xdt&1b=bRa^g~<78{CV3%=M@s3'
    'lk!?mLEO)?4li6(QLlxfg`yo4JI7RD3VJ_nTn;cqYZP8lFgWWn1MMyc`^5X~I{03Bc%uD{`UFa2qzvf8Lgrt2a0&fy%Avjn$4nB3'
    'C}FQR5IX=BO)airb}6_in$iudzvXi$H(3W&{P)SQo<IEFOpQN|WvK$#Ig31n(`qQ;qXSB(POHN~M>w3qP#_fqZT-2R^gBk%z|`fy'
    'A%E{E1O05w+`+Dc|J}4e|E2CO4qNoviqhf&tmX@s#B$B8#shVseRwb~h(p&5S4f)MYdw)<<mgYdkIU{6l!9#JfynjS`qI2i)+4eO'
    'pu{#d0p&|vcU>@*)Ro5|trNTPD3t-^C|OuMxx|0=MP7;VQuHKTJa?i#VP%1{N(+*f?Z^Ffe7=hCwTNrwRxGo}f=KAWjMSYu1hc;t'
    'V$fMfAFK?^p=;LMC+fx%U-ho3Q~WfxWv2c)dRwfpn!398Uv_j=p^5xyYLC+X;4}rfJJoNZ{y=G2ONX;ZaY8;0LvfypmTFyTizb-x'
    '3X`yDv;+>SX{WIAM7L-^H{I9d+rX2I)WIpERhNaTj$Z9i!A_0sTn4O%M?6w-bf^<_X2bQL(#2G7d*uphwm($QDPf=|T&>UOg~6R6'
    '<{w4c--*<MN(rCTU!$B@&v;>Weg%5+`d#TZswA8r_%6}lY9-#Skw2o6u3JgB%=HHxM!2yz9{p6<eT)Qosj1~XJ%E&kQ^FZ6*}$=1'
    'v-=yh<_{)^SV(3KgiTecXm=eBRDEoDW@^EZit-HMlM8)1n>-0CXeh;?qbEjL9x^}@>CyHC+?o6#Sj*^xgB?|jLfvjzY|jJ{C_Px^'
    'SlOy{xa1VpC33ZzEmNrpZ+{+|fC*q0-#q(F*n{HeL3US=3}){YD6Yb@nS^N@8mDR-&1%V<LR%H-X<A9%EW5Kh{Q0tp+GzMn_i}U*'
    '7h;RDNPD;H-Ee=S_i?7q^wW9ju%u!o5etgMpXvAO<0N;^w6@{jKeF}`!XK3+Lft8rl)<=^L~n|EXZP`SR8R)C@W8$nsatEOob=hL'
    '<T$&9Y|w*t#yO|5x!sB+6#Sv2b+V)IGK##2Z?SNV75TE*y)~;V6Fr1>J)DmLHLuA6I+u9Wip=obbtEtifB>}2oWY|aH9HelOtphq'
    'wu*5;mg}-B=vfigtGRkRr}M1Awti<AEDQ4h+R0Rq+Y?fVa}Xv|++KrAabN#rTtYWlxalOxHdn4-*L=yHf7_iY#1!ZBD`P9y)W*??'
    'Aw*O~JE1lLv4CHDli1QHHp*t@`(!COcmxyhEMDnNg~GfHFu0aR*~!bV?ta-e{0#6)lCg|N-<)34oAOS<EJIS1s_eEHJ|j$GAtz^z'
    'Y1rN*8#ApK%<LN|5(zJX7agd+KA+IgO`z748kiC4aCYs35!qII2cX3X3f@6meN|2>@i|R7uER|yKxcjEy;Wy^V6<gRj~c@V=%zk|'
    'VNPZiXQ2xi6lY6r%Mrh>gV)-#sFS8u1DHm4<v@d>Ofyd7k_HE%+-;RC9$~0xn$ry9<H(-O6xZ1lTV`M#=BP2*dy24a$t#Hnu>~OH'
    'SdK8rCgTDRRJK&j@h3{WwAd!32{T`lksVxS4_m|`8_iWG5-{bhBhQr=e~!5_njB$D$)#Z#e4`|dP&is<&(1<oYDrEDkQr8TDQ9>;'
    '(V~#{7-l&V>{dzth%SD9=ku|1YvkZz`q+(2Q2@e>D1n~+fl37cNzQ*a2FrN1n#cFfJ8O%dEEAO&H#Aq58pp4x26i+w(L0vM-2v_3'
    'Pcb)YhY2xxl~?ps8w^$@kdcFK{w-HyUi-WGxh*1=V|HEH3RFhWtK+s&^Yuh^@Q&csKFmAyQac~ics!%*clMV~HRsi<E*$t2?_VZw'
    'OUdE2_OxqdkPC%dVGdIZM)++Lm{K?Q<|btCHym2KmBXuJ{*D3&EZ`HAhQ6s_3%r6*-qq_4892X|kMTBCy~FfrhJtGsKgd)FOqE6*'
    '%6lx~Wi5`or}>1AJBu_po4V^Amvd8_o+2Hm_kHUW=P;|R_xB^_HwfK52LrJnB4SI9(#pGcMyD{O5>{7BScJWFTu8p?!0=H{|I~%#'
    'ro8ZCoBf7cB6-dYgh)9N6geq@ddk7`G4$vhYBE52mm}d@Iabi62-!h{{dhaDAA6pIsnV>#QC7)EFQ#mGyrpewqlX#rp$FdqIKJB$'
    'JUQwJHa$v91Tg`q7sR*kM7Oavfl=P=CCjEavvp}4tAdVdX_5n)zd=`KMc|fCzD!Nqsv?sVhl6Q3RVu7C%|Bo;R_>Qxa{8lrTF%p{'
    'x`|I^@6`a`t@M&Ikf&qC?vl~US>pQDruafxWAZ!IMtZ1ul9^QXa)Vq$Lx4mI=+AHznv{Fpimlv$5U0FlnC2%!l~KbD*XQoA@>E@S'
    '$B|zKboLE&KOyH@)6ngH>if;{ZF*!f@86|K4Xzl2+0n4<+a%qIC)WRsuNGcZed+SSiko$wH~fN%dZmFb%PAs1!QOv`l=}%t{;3YY'
    'X<BR>ey;ML8l0{-%HOkpMhdBQ_e74%sQc_|ARK?8r~Y@f2Ekzf+$FxH3%@beysK5~*px!+NxhOyZGNhBL^RKU4PpRfkkPnQ;qOH5'
    'QaKQwR0|UILXCY{$W4I+0p_5B5O5?Uz9NnwI2uToT@O`OOB9hsjzQzsJU6l!PWGbdK2Mh|V=F8ADO8*>*^h+Iwj=PHL~D)yg$vHV'
    'cw{_zAN*<6+OjUtpKnA)SagUj^3-_t63#YfOYp{O+309f4xK^epCkO<icX@D`ZzbOg6m_4*yOI>M{^+Zc}5dw|JI@GMqO0MCJ|g|'
    'E3H=Sr1;gD2AY(pLN#@VJA#I*iJJ9h>haL~Csi<bEh$#_FZ4ok=eDuUoIlRdsv=+R!frV7x_eCyV!65-1w6r6y%l_Hg06J7&IuY}'
    '&LTU_rX(BjLCnuYNlF%hIP_y=GoqNFTy(xTbet^;3aBqI4KH5ME`9=&_PE?y5GkG8+Y1tdc%46def*+1@?qY;ffe8015n}XlR6U6'
    'eG88aJ#>=(*vnIf>KSM@LJ>dlK*;mlaL+@N9cxrrNOT!GO3!zCV*AxG_b<|IJCXh$9vIu>hs-8E)&YAvCOVWlk#w*)OTogQc2bt8'
    'u(o*?Oalox_dR@gpZ83@(|9JIINkyfxeMuX<Wogj0;rkXwwl~@*YKHcTlD)f?C?{$6cNhUKzWqmM{ZuhrVUNXW8?ICC0SHT$KmpP'
    '*S&?4o&J%*KsJO>G80IXV}md5uGYha)?#xP3x!{PeEjs`&tD%SoozA%*?>?uoux(u^?5;vLoid-SR91f^z5Mc+#m(x$Za_lz<x#L'
    'w$MnEFNP73Nl$#GS---7$Kd&+D0Z@CFKoohCU`?f+CS@$S3c>3?5?Znm#MCnl~U+Ah~^-5@pPocb={e}<ROTouqxCF&*mDthzR~n'
    '@?byD-LL5^WZ^letnH!l#LJr>mX|_e>FIW*<Ha}RZi+fZ+oQ>IOdJ~Yn#1&qZM}gmTD{~BVNF?+#8Mnn7Z`$4q~g@$;?0H(&DhOc'
    '2iT)PU7VkbJtH6}rNnJIi0Sx*gUI3(%y%yu2WxJ^NP9C^+B34$5s;W5y-BY-inWCUYq3**qcPaY?BHwg3Su+|C^KX$El<9N<b}Sr'
    'S5**5B}?FnAg)DoP&nikpmUUJn@yJ@0a;77ZEz&8M_4y#AKzh}T<3qZ5wy#ut4-Jn0M{Se-x~YQQK7ew7SHIO5Dc68MRM8}?53Xj'
    '!7HVouUc-fqa+l-=%-HozS=$6xVS$_55EUC$iu^3`7Hr1pM%mjptCLcso2xQuS{M3v!riqC%t_1(*hoB^0+=vrM*zKhdxy!;KB+p'
    'Zf8ckq&_7=bY27L1W`D;D%}Dl=C}LPIg<Kbj{ml(%sR-{JA-z74q7EFSgx8L4~AJ}=Q$}FtMTY+qR`uSIM`WFGS#cIGTcm3WV`w8'
    '2GOaEA|%8VSQ-ept4G?l_PvzoeM`;J;KI|wc4TW$x%-l_kZ|Z^!^zn&l~z93426X4cxiF27o9`#xIo18il(5g@iG>`0{TN^LnB4X'
    'X#ih!5V-hMXgGotZi+29r59eZIv@r{D>rSinx1NejE1gL!d;om31X3OUmc<bZBFu2Xvq_+Wn!PQ<-POcNvRh0A|Paba66L9pDrN0'
    'PfSXH^f^;+QyBgQd%KUgr0&PoZ4G!rvs2n_|08wSZQDA`p%IVjbE3UTvV&RCT;eeQIYjgK$ItJ-KN630qQ-o<&j6M_Z$CZ$p$Dy&'
    'J0~4#Eug6O)(j?xmqjQWh?~+wpUN>$)=5v2=c;USxFoAfviesMc5HXaRF_P3$y76Csw~g|9cRK!IlU}db~o133;C2*Cog(QX_u5%'
    '#{NldrwVbPnR8T%p?}F_mrQoaWd91dM?CrZaGtB*-ob|UVFt@BGA9OSkW9&ZO5wib&V!fhZgoa&o(VIql3gWVLOR#kRG0grSCi=)'
    ')_iA{?D<~#e}8}T{|@h&_**<FC2`~xTr+R-{MRHO3UB4Z-C^{HpGV%zE%Wo&t9bv%$ItKgH~HgkA<pL1H+}o}cKZcm+~hhFUq1f&'
    '`;RY&zp&PoAUd@<`>>3!-u|EYd!<A=430PX%a4zrKK%LfFMt0bu$e!2f6t^D!|(6ZLw1VDBdsw$AafJnv(MJYZzL|G*+WOi@QRM*'
    'zGrDEQ^NjrGJX3?;P=e!apYV&x{Eyv@^eT0@%`9uRsPE(>$a~{D_gfKvOkzR1P9)n!SPkWbxb+Bv9>!TbS6<c_<}fRPzDM?<-<Qc'
    'o15ZPNS)42a!LL%M#c1t^8T}5_x!hYPGCibOve}DNV}z6A)Qt0KaBFI!hQ+aw`3W%GM277BjwggmXWUg8A*P6pni(yA9h8F3q364'
    'i7T$!=Ua!=O!Jbt;3_vaSr+H1>ROoTDW~EYO)F^6?~+5l`Sbn$V#!vaLk<bPlO8!_L5FmGIVAUTeXnSKfRA#v8P6u2Op1~&hDxft'
    'Zz>p>;k?2BX`5L@aJ}}Ln}xqB)#Z;pZj3%6`B5j$_QF3gDEjo0tDgful0!0Oe#Xld*!ubrl!RJ<+#Bh|r6iqLJtX4d9|d=k^Yej?'
    '49BTk-*D3ttiKR%hTP#R0#WzIk{i4GRVAtP{t5$NpuC+eC{ohOuP`Kn*MP~o7n$mEmO@4N*51Ph=|r8Z+49?K?m8;G`7TR!S*lAf'
    'zpDTK&wsel&?(c689TpmaY2x35<A#ek|Q?NOg7-~1<glxa1AuD4X;(v%1`q53_o6R4hhqVQaQGLGGU2Nij^<R0PX$ma%1PU#DTw{'
    'peYG!%m6)S*p4vhW6RD40`EZX1E&ge3hESF1#a}`nY8a}%lIlwT~X3r1<F~B16fT$^Affr)QKt|MCy`#xK(x&!Z1Z7w_<20IX&W_'
    '75PM7$8*u`btFmK9w@zBkt3A99#zHJKY%nDQn)wBP*9AQgr(VK2sQJl>bf~=#5#pi>bJG{m{DBH;7Ex#;RkeZdkRW5f8V87=U4W|'
    'l5D$rdqrO#U6|<5%aya+p2|&R5CwNy)<bWtjlv|~z^1%1+P{q)(n?wVqBb{~Rtl#wBbc95TR5zA3B~KM<abH;Oeq^1{FpW`b?>dP'
    'CfDJ#v7jCI3Z`Rhq?Vj{Jum^5nnKb_Zt#|10=sV{c|F5x#II0;gUf5h;BtCE0*kq<-V#paP>vN@=3;lA=~B}*MGat^&x(}8;@}(7'
    '8i6TZT3JRs>H15VIGFq@8;nNK0k-93&om2{I)Zs-=(lU0p_d%aN=?AE@;x2%$;+&^<rFqn&6{{i9_DW<qew*pyH8<LGNY^Hdr83>'
    '-5H<gkI&JVe6uT*cGYjJYVQ5TGE90(B^j2!22e+SB$bk+>odk;hXK42sa2Cth<1ymSzZFQ;hh9!jzCAr^5A;&3eKf?G9A&$R-9HP'
    'Eu2)bnK?gDhtXN|lZ8?P==;<V`Rp>=_>Z>+Q!`B@V`K>>1jye$OO_J8&JSN7zqFnbg|JVzYoei+XfaIgO)%ra2&=%(<Is}#lgp4N'
    '9WG8xOR7ZUm%eU7;AH=YZ#1TBvD<rY@YZfvmb<%!emfPrnVaHD+3vGx$;O_S+?HKo3PQif%I2srU9g0wrt{_4)sWl}jnt)D<I@-H'
    'fv10(9<CFIo#+;Eyruu```7ooU$$Sr{s*f`l1M1so0~4!P<D($S+$4dYhJ71Nz{ArJ*lvWb<(7QBt3f<4dk(d_#+8i=tK^0I<@K*'
    'pJi{<FR`6IFDBz#p}L>Jv!nY=ORPK7o~l1u1Nd&OPY?aIOY>()^__-BX)U59u{fReb$>;EZ1xpt_rH_Ov$`txiu8Sxl=sj`<F=tF'
    '=4kV$)7tHwCvXq`^cp)U;FId6=1MYj3^MhaNY3i){>gM$V|xyDlvv3s<t}q$5Oj1>SHD_5?_xnu@&H!2dwhKQSFbkHkD&U5ghEvK'
    '`Eos3u$N(vKQDKIjCo4)?c2Y%+b>>0-B`*;`L?kyb5ML0jy{LTxc{!Y2*x#bq>!}0W2O1CpI#Fo@imoS&&#F{r_h)cH6%LCj-FHl'
    'w?MVvw{C!t>x#feDCq0^<;TZQAO8GVQGEYl0HG;*jYoeGd^pp{kcF#o<j4u8d8waBORb25Yl5;C(Cj7>6xql<dqxCC0}$QVa0?~$'
    'S6v=^V@OJdlIa=om=-o5VpDkWYk-9$?@<d+li1d-xx!_4tWhl`SKFiYV$Bhtq~EVhXl(2*5$+!)CC2D8Vd*VI>C@yp4}@nP`o;{~'
    'xD;J|-QrZ(-<?M?EiIu*4&=v9iqU`0isP5~`sIitFrUT%`%^-{jR49QXEV#PO}(s1y?M^COc(6hHQ5znPPv>*@?YipttRm=o~&9X'
    '&65DZt-$1zI)=l*M2>N;LgHCgY~byA{%P>aHQUcpwAlR`PnM6x+PtX|tWSLk?Ol^^h!lfLO+~s8vSSZl|GI*oN_0{I{9CFmsrH91'
    '(}3@_G?{-hZWA!_&+Et!L$Z`Y*(0Izz>ah;5<4eLNK3hTdMu)A+&RK1n2|q1qATh)`gQq657ulAOdZGecG59f1Y8vW(xiZM_@u0W'
    '9Fr260CS*(zoITpr7`B<rl5~Dor-L<?@!f5CF5y*-`0hA?6qAj9HbHeb!@kP`1o4|Ch?j?B;|;P>=K6SwItM$%_c#io7Rw{^nELo'
    '<Sp476-k(fbdo|H1mC=n6JW)#7y0$H1r14^K1+m}QFKaYd=UCewZyz$5TPm4^0ouF#>ECo2@|bkXI?<t^8zaC_khujb&e%5?10Of'
    'tm9Kk3+Q`c<4y}Pcx6!ItcGh$!TP%8++(r&_S7oZIq76_%oyfhqYz5+7a$FiVCo#~c|R9%`uy?J?@#{!ofZ0eq{+JXeE&S*@E=1Z'
    'h<$><2QTPqBhMIR{-lj(<LKWU<xQMP55oXnR_r%br5geU9fBF+W$(d!H!On$bL<V}{pDZW5hcy!y=V8WZY=)k8ZWrOZWUnQF;~{v'
    'XEBA1AeD~48AYBpb)HDYk4{z!U79d9CaFM7i<VVhVH@eqr=-o4o<0QyO-Tw4PS_<yD&!$B%H%PCJ9PyQn?vK(tMPnF<pw1hzT(_M'
    '8HlmDQ?~q7W4+0x3?J9Q_n#*tvJMAU0AUw3`%Z|?+_^hcDTHG?7A*0Sz#J<%874AW2fr*B6Ray^1u%KEjL6+tibkyD@q=b4{}sGT'
    'T|wP6wAS<WR&@nMqXPY!D)?EA0FOV3Wp@I(Tg@rSb%)rOndbV1IUks`Gdu2<=6ItNN$QHhW|_KUwo$@aAj;i?FyUY?kUeXYqPlqT'
    '3_sq!4`C7V<p+*iK)(W;Da<7G#GK%aX*!O>VO(WU?F&NcL13o+&wseq&?pXn#=DE~JN&6QShKvx8AGbx)OHn?k~#|1`BI-M5mIf&'
    'CPHZjqzyE=&Zw*1Y0zp5Z@~BEw%)NnS-+m)hMz)O{eTa&dwhJFD{dP3dJCPF%NO0Ith=|q&ko_D+Mq-%6_)9%?}{V^YI*{x{GbYy'
    'IciY_I@~rd?d3cis9TZ|I<l}s@mPIPKblP;hvzbGVUvKchH*fG6?J0{PiY4yTUJT#r`E=vjD5Z2HQn)KxogczT+I3&nl?p;dC$!#'
    'd^C~X)hsqPid$lo${f*l^|&-O_$k=rjs2v<SZ*0FQZO=_P|(#e=v)@5DW_^Rl;(w=_6B@S5|7orRzp+qB<Lc%v)-|6GjM}oj+bj+'
    'P6j2{m1$^0T#ivEM<$b$X-Z)VC6&Lg61&^<Vt>|tbkKI~6k-)N$nEwBs<WenGLjQE2bn!=%5bn$*ovbHl2;!z<WWl#0&b^GGYjY|'
    'gAsGvGh!N_|0`)EaJC2+jD5kUiquBjX!U|mIk0}C1;A)9BrUD$6$#r)B~HKx=_+TVG}@gX-%HBFO5Yh$bz~VmjibTxF$d6*^f{VJ'
    'Q$>pssX<OD!8W<!01_QJbVB%-neayRpQTrlZ4V2e<Vw&=Yh|u1J@8E*VuW6W@4(e;`|0tI5nD4fa4ZXrK3l9f5u5!HW@&qI5wVji'
    'Qh!k@RHLy#eu~w)&Xh#QEC&-ol1jenfNm9o(2HgxMy|E4izUimHzy4(3EhBmWsN~$+VhwRfL#xt0O9tmZ;=s4h%@Me6$rV5>Ny4x'
    '%^KP+O&H|^KL>hHwD%a>jy~NA_1?O2oG5wjFgq+`;&I^T3~VMLsxh{6a4R&=^&pqjV*&QdkB^@|{Q2c)>HC9YK#%|~{Z8zE%dNNs'
    '+!?a0W0-7^<928uIYj)U?2I7~`-7JA$4|dM`Tze{df>9+X{rsnVyq%s`Ztl4Yl>e;<iO{V^D}m`_PA`#ngRnaJ;!@^pe%f9|0JJO'
    'SC=^OLVOjr!dDCO1)p|dw2=dsRPhMAIf<hPrN*OYrrHs{Ue~&f4PPcuU~f~UH(CLh1MOtglu~VrAbHsfi!r1WLd(w~vWnMO3^(ut'
    '%Ewe6J3{UKmSl*MWq6wc3O&diU-sYn`q#(DFB2Fcx*BBBq1Rg-W3hbL7uUK!kDHm_J1Q6fw@n}gDf%mkrJ}?KMD)Z_3hHX({AWS&'
    ';eV1H)o<UwzTf?_{rdGkjiCSvzA72Y`G5~LK9ZP|f){k8ntc*d_yt4|t|_)&?5ak#FIYv{ExERRqEV!i*d^*>w=q_Pb}R-Aa-WW{'
    'lc+5UqVC*Ke=&_LHQKYg&j_D@J*nZbpX#g*jQsEV)TcR=pJl~p5K40HHh2iI(gtg*1ajd>7N9kyK<rui`sEY}XEu*JvIKRgG_%LJ'
    'MYLu9D|a&Vn$?<H)f~7cAEVPmua7~S5Oo|lqs7_Qa7MBp+jhRAJMqnXk?|a7(74xW5m|TWc$)9+W!W^Rr)j7)=j*atO3;gKWQ~WB'
    'nm1%Iy<jWKBBP^?{~Y!R2kScOsFVs@3sl%&8WUscG$zYHLrEq_|N6&TD?XLMN>J^~OxA`DgSupgbj>GkSy9;6wvg=>7H90WU5v@M'
    '9A;Vx)m!2cej_(!wBCI67iCzTQB0kZPBALtEl1<&$v9;WWwcd?(zDnZv)#Nt%f(&WsY?P_QvC6XD|ZRr7iM=)k@R!|4mwh%nhM?5'
    'CAlu}mXj2VVow)UZF$x92%0?3_6cqW-+!y&N}nP*p9h^^%zKAERddy(y}(rFfo+(kPP@#f)#!*Y-tO`7(?SMGysQkZ?4}g+grZId'
    '+yapxcv`rY^S_U2LGRO%uBmIc!#7N7pQ0dtjfg~@u0v_TM9{J&Q#_L@n0ZE6Vy7%j-bjMU8F`UxWRz}_U$28VeO-If>;$Jrs)P{E'
    'opf4$ecju4U8({WB14|)7Do7vb{4&y#Nsial<JKvY*w(T?Qu$D8tCsE_6DoKPL;vug%IPgAbD3wSw5h|Wf;t_26KmFppYDJ`Km1g'
    'd|Szo2F1bCM@7rz4%Bj}o_-UzB}2f>N+PM#aIjD}9n)v54DlWRWD}Exxr2Bk+A*b!N-?tE{pEzPTleAPZ`0U2OaUoxS6`47tGvEY'
    'HkOdHp<8c&B_p7RzmhoBa_gt+2Fn7H)PNoYmIal>8c%)@dT+_pk~UD)NsP+ayV1uaKSQ!9yPd#nfmObee52Ni#Lf|%>R)?XTz(<l'
    'GU`*dDrElk1x?=@b6;!5BytR^kQJKQ>#Qb}NYD?<sW1POk}$9uC=fcx>5E4&u5!+N%HF<1F=BQM!))tsaZXs9QxiYqQFA5?h#-sD'
    'eDIH=uS2rA{nQw={T?2+8$bnCD=KzslP>)11}m|qzZ&8j4pU(nwHJ;nf{nqat9zl;FoOw-5vA*$LtWY+QjWfi(cB?sf%C?-tWX)c'
    'WDYHR>D{`Mp)7lxm330`he5nDK`lebn_gk-sb$fWiZb**RBMYsr(IZuAvHl>4_1$rHb6VXa-yXHS=a~DXYgib3;z0o3C|U^z&~Ac'
    'CwlUOZAnx*Ne57r?Dtd!VKKp8nP7)80SFKGdPz%o41l6SQ()osko+8D`7Xj9p_Nx!Pynr!0|~hiq^YUuU@wA(LN~VhWYH-ZKBuJS'
    'S&Ez;Sc2vbU7abZIh5<~=;EMXR{yC!d)!i@zY22*K}B$awQ&;~xdizv8<fs+^oegSoR$mo#m0O=s~SujA96mh;61lAL?QFb1NWzQ'
    'Jp<d)Xd(Gg*R?Pl+IEJA*c?ROeNS!|<1>IFv>k&bE#sgYWNWA6k->f{L7T;TiW{?U(s`^~L?xLGnGOn7CdrV-vq*U;WOJ8{!2W(a'
    '=ANX%y{<31S)oTKG;~gvI4{jrDr%Q{(-`Kwk^mr-thjm~42L!*N|ASXhUE`~vIBa`a=|X#VLU<%WdfSlX=fX$+0}Zm`Ss^KT<d62'
    ')@&4A>WO0NkK<#KMV_Ey(4k#~hMEKR)Mcr_XuRgHMA$stgo!3cgGvxp!urAi$%RE<9L%2?fZWRR1kE&LebS{aeLW=$n?WX>gP_oJ'
    '$r+NXD0a%qtD>0%kBRX^X#$_f)DYjo8#KT^9Hpoc+b;wNk+y+kMPaH#aiXxV5X~Juj(${C^`Z8FYR^lqbB?vNn^DpU+d9dxPK*U;'
    '2M?}SVS>Z?)|}wR-0B8w3MS9Zg?-bE$rEIJ-S)P*iJl<PL&d9C15|7&!d61}xoZ;Mxpu8Q=uYIv>xOt2xYwigkZ5n`fVTL9ppuT6'
    '7>+7FT+&Rj^O<kim$aHt!5qfeA4PXoG-(H5v^VB!vLbqKhBQwrCuDZfL3E}|pP!NV-OLo2ZE-(gQ@y>-VToDvrcoM-yz!GI6osH8'
    '=Ey>af)=T2PX$^b9~hGf(o37CkNI-VVMBq*MyZ-N5Qp5!CzCQ-SJVX6T>~zp?w$CS4<COs(-J(l>b8_5*5<lH70J%kN)1p_hf9B7'
    'wt6cqc4k42bJfryH=3AasMl9ftiY&af-wV2p|AvtCYA8PrK`ijON^QrR4eMQhs;fr9y>S=R|AwQE&z)(rhJh5{F$rX!f4CNA*Qdq'
    'Y*3cY?PMIM0dSKH5Yn{6P)kmZ+je-!p%)f%EroXs^BvK|uBjq=z;!(Qb&a~F^;bv(;8iJr*2m;-fK1!67*BcKz#13m436dIItVUG'
    '(yh-Qi4;CZFV|>T88VWyeV&U1w^ZjeolQq?KqA_bij%e!M4e@!-&{@E++IScyw)|j(azIVfTeaJNsfG~6FLMYH`E%jwWM(7Sb4xD'
    '{oD7i?{~j!zkdDCDTApnZRixsI_0%?@DAUte_Ndig0f(A08ne4c+mTmLZv>(nnN>SEDHQ;f+RT=Rn1kz#oo=z6B+O&5SA|p#%+Bc'
    'M$&p{kSK&HfbD}7&4X5(L|6q>wA~Ho5ER<N9(R4j$324$lC@<3oGd_|(jG}ZxMeos$RTV&$cRpoaBb!;MgS6fIthy!b~Ia6)kwQ*'
    '-m=ETbwekv2G|LHl!?rNrRfAMA;R_-`^4N6UEG`6fig<D%5{Hq9q}7O{bQib*?I3|MMPfq6p-57EWr+vWu3`qDcg9-AAJIW1@g#N'
    '`)=zoZQ%v7s$|L9`oPEy_v$-C^3H>!RsyitV$H^#uq_?u(V7b-_(TK;T{XUm(@2l)blrxIGBgfau;2DiQqL*#94lYQ>c_#&=dDsn'
    '#ZPD&$xZuBqT_9i|HJ0dEeTYN#DPa6J6`hoSVC54kfR#Uy~r+=G+`T2Mzml~J3=>Ue`3E+l-W#<^e2)AI%=O+^iYu>7Y>p~_@|%M'
    'oV~iy-Yp;c4tgAFS`LP|<zstqt)hlPDR>tK-oKhL@N&&`h{QwICTQnp0oCoM6wk8w%>$>;DbCz^>%9nP?t12pFoRiTi85mS7NwEL'
    ';z%(_gj)y#nk-f@#qYzAL>)579wAMpsOQS%P+(SgjBvVSn9f>yuVrw-{%lD*S&^O934My#b8)zF8Ii7Zz<){3IuE1^e^3vlbIc9b'
    '<7+@`x>4?L6+;gP0C76C038V)ef<{u9bK8!QDXPna0;UAl4wzrC1NF<0v8;QwWz?jPozbtmoRTEnm@xW0AXeBI9xj*=DlqQ(vrd='
    '(t=9f7zCWQO}Kp>&`R*8rSE>af-8w(wx$jgc*NemEs${O2I}WOSKccy7yz>g3H2O6Pe-!B^4gkHyK<5<Z!{YVIg&9^V)EM2ca9aT'
    'AVIgRK|?)#VwmI})?>LEfsyAzjlQ6>#1AqD>I^`XT6&GN=(1?{6TyC03=t>~B{U;fcFx23>iiN`)L^-A4we(7=@**xqMdB=2axZq'
    '%+W4J8h)!O;^(K3kR`nGoe8V5x8=!6XG2Eb7wes(b&b-L@tVT#euS!*GZb#%Id?GtTpnQyj=+8R{6PVBtKst<LJr?vNO%`QpQ_Y_'
    '9tv-XY|ANxf|ixm32!sio_SjB!u=D}AS_tM1t4EH#r@~``GM&(@_ryNpVr5g`6sESi`gd{RFWK_sc03SE{9($A?;P9xj6;DS#(Y&'
    'ZXF897R5-T{*09G82lI=lBfY(Tj5(?R9;-NqhveQG0?6dyZ{A6@0Rq)lqrcaH8!fz028@{_oIqS?gY}<y{qV;)zT#8km&?Ze_u;j'
    '>(1`S&QtbbO1RB)M=tz2MT83LIR~*MHFlJ1>cS>86PShzi#z&ll1eJ{vl&z`cqw^bax>M7u!s_Q<%v?9)D~x^Tqh9@%R$rFA13ul'
    'uy~i_4$|T_aQE(-#qN_0az`ISti9RNNJCh><qsCPo`d;SWB?baspWFvE9l{o-c63=XE~~!;uu2tc)NoWd_wVsR|CO>^)%HSlybg1'
    'toO-64{nqhF-K2C2W@l+4s~hXrXj)s34@BXT1j^vl4l_5M^aM{T~hS!LedJ+KdGdn)kJNWq45$eG5;ka(Dpi+XM<jiA^y-pqdNoA'
    'PmG<CecC6fUdXdQ6Zv_$l?yF)=u<xO><M<|qzqbvPbc;04#P~O*gAa3cZqK~5r><Z_ghOl%_dHuC)WEKy78g?7YQ`mA5kP_*6?7Y'
    'Am{521X4rG5eU7MGbKTiwMq$3rcl0Mp<zG?HEsf$VJ<*my1RYZ6*h`w!BHjrTrn5Rvg%P>h6S`PAEA+@O&aa6CZ7%Z7$hrH$5^$h'
    'WE$8hZCvgx=BK*yl>Jx>`y#7IjKu=gL11!~Ox<i-H|4WrIkHDbv3D>K3{EXon)2BswS*f~4?>_RBfV;%O95^{hBWY5r*9n<JQqRP'
    't*xxkps^Ik=*>ZT;QG9LT?ZIU6=knWvC~zlJ>m-px*<%~GZwN~s+>_asEkqp!3A*J_rVNvT*Oai2CAqsvSw`IbA^nS_?>_yo1t7d'
    'n19#Ea1v!Ok)#rfa3Jc@mmH<HybI@|i?mB4i&&P|l)izIU?gYiiP=BiYodqkq<|v{SSeqIMoM`H>Zo)h{I#bKNi&ebRL+gD%!cJn'
    '&3vkEEYD5T(5(LyXh2Rr7u*855aL42<_pzr=u<TcG6NK^6a1AsssgHI#G${Cyvt6@iaX_6d6W3Al$U6uy_st8hh1xE)l;w|>u_U3'
    '$Asm3v`0{(ZBn!^hKIYs$uKzt?H@H@ei38)OF~8lz{zDopWd{Bm84VAbl8!ilW;8}+voP-(7S|76Iv)0rhlP{{>8nwR`(Bhu<dd7'
    'V&Uimu>5+){e1XO9%hSbhp-<LI!KFMqI^;rrfm;b@B%wO17bCI+wAY&?UpmqLa{1v>+t4F)?VsxlH3F>Rw}*CR7ud?uoy>R!f<uI'
    'p<h8yO?5Xq8$IGBWWJcMW#^(Wv3MyrnM(r=fz7Wmot+&A{SHK#<cjPrep|ev0&DnJ?&gHvyvf5|Unr&~PV`1cJLhQl81CF?2HI75'
    'z}!^>Fi;X5dsp0g8iTr-o0OftvimNoz1Fvyf?>P44QTX0L6=6?d0XIS^|pNK$r>GyIVxVbkD5@u#X2h^*VCl*AbB~3rTVsQIxA>x'
    '!A80Kc9F}imZ79h`4XPjm)ooHZmB)426Ux^3j2YVST`kbMQz-qUtYWjyYcsWOGN}{bJD{bzoYfzO;3Jn>&xbA_!JB8jF7&rhExD%'
    'BF{$N#(Af(3%T~hr)v7gwT5*fs#=Ak-Gwjv0$=vsR2xMJpxJh1oT7gdC2FMJtdHOWi_Lb>Z7U!__K$^eKndB?$aUz8v<7t}RxOa-'
    'N|cc{6o^)LA5@Bk&d|v4kzRHdf3#p+L`$wq{TnNFCxs;_oW;>s4io6=(IbTpR^>QrgLMTdSR!Dt*bA63$EvA0>a@0sY{hv5V}595'
    'vFDZ?kh#LC0V~r02sglXaolwe4N3kCArDpjHb~Y_v@_9U#S`mBAr>RCIHPswe@Kohpx8kb)r9M@3@I8!``j1D>xYlOb-E8`>;;VM'
    '^KAQ*#<*DAkLo8nm`SMF6IqF1W$)be(!6ZDOL<T674UfasBcj1{M{+Cmfx+l4@!!bXjc<ed=MWrVmjPf+n_i!IK9j!`($>q6s!G{'
    '0lgyo!+57UO6j<pxx*S&sM1#S;T`xq%7wIxJM2n&RgLE~X_#>>cu%Pt{IXD<op!pJsVXg}V*Q%#%y$=#p#JK`-_f&CIGL4?%PqRS'
    'jo^qb6<OFha|L8fBu9Pu`uO3;uiww5sfX9XW4tgBhd#AjJz%SI_hKgowf3IE=4>M#;;F0Tc?M=Nr|~ZFT}O(&t5;yX8`Y_RxW)#c'
    'vcYRIhY9iVA{{0i_0~&gIOV0B%IpZL3+l-MZ*3v#Glzj^Czmk~^cC(Avx0sWlB6Oga!m=p7aPv1c5vuWT>(ikvbO1t#gfobPf4)W'
    'IzSIwW>}oTc`BMPFE$nN@KhRZ3vli1qM@R$vI)7qnuENwvnJnd0LpaUm>*E$z$mPjV2Bnm_3kWvaHrA^P$4LEGYO2u-t9swAh`jC'
    'njx$xyK@-h7O<L%pfwDSk}qw7@+k(CVXZ7dDl-dmFCQii*H;;~b4`I2MH>nY5)29)^)OyzW~wZE%KUF@&L$6bGW)iBy5^*06Tn~t'
    '0sJ0C;XY3ARq=LRjrbztE&qCHi%t2hE&m75dOjYOD=em@jpbG(yxiMeE1?OEHPTnI&v7M`hc{-XT-#{@XZ^Z1sB~4nrPU^Mdo#N7'
    ')_d5!8dpg=6d2aVJmj~$J6GhL+-Zm`7xEir(sx_i{IiqV7VrF5V(Ey&P*DeND2&ON>iFb)&*anJL~o<@S;YfUAR$>2Kz%M0gw6`}'
    'Z{J{6MvnUW@GKk%h|n0rVjp7%F%7F?l6?Kijjrfx_kgK`j2vL$5LU?;P6DKiWvT-FEQ_F{VY{KMPoDlxbwY<hgR=Rb4qgNCQlHM-'
    'vn*3L1Qc0IN>ak5;4~z#DJ0TUw+@FVZEg8xF>+Ls3w>}D&%B=YXTU({4&fb~6+XASZ6YVgL2M`iW!sgmXvCk()sNUC5AAHykWOKJ'
    'wObR_GgZqQq$Ogdypp>shu6Vsnv=RGJXvT@!QUq!EU-Ljv!rDT++WA%s|a5r;?7ChVh$d1kUD8fBTFMP)PK(>U%x|dq{`8<y`!yX'
    'TPlky2T-8u3@hQZ>&hk*Bg)imGyT~(rY~)EvU%IWAilKPqE{1ztif4a%`wF-h&mQrXwM?Nz+}%97QT+5PeP#~5$b&Ur}>7d#l_1b'
    '4y=<JDe^8`=Kr(&+{y%6SCX7=8DY+1CuZORbG)GQ@zHNPMblHdd{0D@dS!&bL$>JA__z}Zxs(!{sJ})TiJdWX>ih~uaT0<1WPnc^'
    'rXX(;-*qJGZklY`1EU3aTcQ|?dIzJfKeErP0EJed)VS!U!cHTkNU4~wC8SG@w0@Od6~dua(D_6-3~Xw)BBF0*k0c8TEVBk>^TC>a'
    't^j7HKDIiT$_+Aw!spg&vtisxk*R2!Co35TxC)<|PXL<FpHH>S8#tm-a5QQ;r_FCY6}Xj$o*ejBRWdEP+vz~~YSlyEnTa~P!GmfP'
    '^+z9bM<{RyP0I(_yJ!h*mf!m79ZE<@qZ%@!ehP&Wob(VBwv*6HrQnRKM^%ej136i3&k>V}x0nqI%A|C69C`HV0rciw3-GDqmI>ea'
    'yO;r3`d`Vr*6X`%s#U|#>j!_@qQ!th(8L#ZDPEG@?+?9av{jYJ@5g2{LyG{jl3?l9oS5NaAU)6=1Ra+b7$<Wad>u2ivc%U;xS)xA'
    '8R)kuulD771e3_+Bu$~jVxaI)Qm-UNZX>jutICA+M!~w;q;_Q4Si?+RFF30-($t&;Yg&BFg*S~H(B4O-HMj-N?qi6yJb=0>M6J0_'
    'Fmw)v0N1)x5B|9#CeiEmDU9AVAPyYb+p%#If$e;Xb$9z}!}nQe(DADjyl!KjH-V)iQWQxeg}qjQeJ-U*VTtZ&n~ReW0fNQ_%EoiM'
    ';hiDwTf!$R?%tVa)QhDj<xtfkO@8jPua8{E@IZ6#@9($r`%EbD&aS`7z23erNP=HUdIUOEN838QHm!Qn>PF;}a2@mpr&Cu>t3~Th'
    'srm{34yF+8kFuU0m7bD`#F&LP6MdFO-fPd&Ntz7NLW#W&7CY%gcNs4~q`~aMQ7Cr?BP%o*bCo91MPteVL9RNF%aP&(>o7%W$X*77'
    '-9euBK4JbVu>6AS!yIC_L<=6h?^Iq&n$l%FVhRp(Y_ewq-sG%(eYA0irUP^;>5wk+I*@DIXQ3BBazliZN!Y4H_n>o3dGwb=1{@x('
    'm}oOREyuh@I<!ub_+0|<dFVNI9!FWSHF78(eeA}0!GN;W&fpObe_IU=e_>!}#_`XV^Y|8gXKgyS9jBq}5wRYtv7Ti0+t_Xv`8R0|'
    '0in*sD;#i1$4KnevZ4prVD={A3#CiQaD-o%N4QvL(sc>a&&eDxObNaqKxo@^zOJ*QD%i3SWoNR#v}$q|AtDa=NFILKkp1a_58?jz'
    '-&T<`H|Nili?gJ4vIX-mT2L}?n?OGT&4~<Gdt#1gk$?(#%S4H!4j&t`IF1f<4aDh}nyj6o4j!bHQvp#7HyU*ch5e@+mQFu**qIWl'
    ');3D^QZN!FPxlwy^+kh8>{ix^@0x3>GvRP@U*W;w5Lk0CAuQ7LFXl(1VufYw8(VdhG1<L)rV*foXGX#bhIbC{Rm8v)8UyF5CwVkg'
    'F2N1qwkj3!DOEZ9YO<ONh58%XLJpw>AieucJWbUD*}8!p+d43odLCV=YO265Ov&3UhLU^S2iGJa1)P=oBEdmqbey2l<G4Qw3Pp>P'
    ')f9_JWY5Cgc1^V0)R}4FETGdg8WT;1PTu2AL(ENe1WaATsuGG+fQFIxyyBg+8#P`nf!pa#8$=75aP(pvxpGVaG=4}xx?cK{R)!C3'
    '*^Yv%mh{)pQZxguA`M_#YZ^Hju2bYpQ=Z((dVufA^{DksJzCue(m}LsSKVDrQQgT4A)OjOeUoDGMs8Qy9{LtBa+Nasclw)-DzvN{'
    'k~A)E%jF9eP@zBRp*H4Pemb`H)ji2Id`cX`$c6;N@D)-6C!l1du6L&?LB%Mnfd?7*r>yhAQhF8tdlr})kFpx?6YaEvc1}hiZTs7A'
    'ffst}e}{7MiQl}*{Nw~5J-!IlXwO(@#%A=|rjb+o<Y}uBU3xH2ehemyWRTHVE8*`nLS3XHPpIHt?8`!u!z9)whsc52HzDG=ID+74'
    'Af+5Vj4dtrSr$14@jmmM!eTbmi!Js%UABxZv0<_F0AyRfp|kA>0N?<Cab5lk7o30b$awNT_|wV(&K_Y=2AdlW`pcq2Y`{(WTyxf<'
    'j89KgqfI$<ij;qj@OvvdiAL(<-0TXjj~y~wyLv~bfyn2D?GEdiw@FFi4rRB4FyQFxC^ghC20gZ#noVt?n!3XsLDG1BaiFj`t}^vF'
    'Xq@VjG+_~8p%;=nw~cM){BiD3<kIWp%j@nnS%c*2ZWR6mW0hC%u?f1;**YiaIb}!2vk*|rAC-{)ce+J)bOkLRBbyNdv&e&%cK!L{'
    'P!zTBrb!Dv9BjOxUHk+z?Xj=3AW}NFw<R3B)H;9o`uIh2<im_~124C|U6BCTnL82;G**E^D{6Jsz6F+Np@`%XPCO9uJU86)ToKPR'
    'v_&&jK8Y?vN9p-aPi((B=Ke))h$qtj!^1md3qNEw@v#or+qZAaPb3{I&Qh@Or=65DDy(gu1=BzR&V3Ib-sgQC?=-%SCyuuOMD9Ym'
    '9Qjm{wg7oaCO;J;H{CUSrrQ?%KGIt<Q_3E&FgH*hW%!YsSFmYAlk(U&y<UM3)ef#=k)KFSJzF^0=^q&kWJ3rgGl4WYHu&0D7@}P|'
    '3$pQ-A0Iz``19AtNN1Z2!Tu(OsS!baUJ&9C%v3cN2a)yONf)0Rq+lGmEvEu_cI#~+G_t6TBpG;$Y1<vFYsZS6SP-Jt8mT{tL_@ah'
    'wYbot(ZJ?6|Exb=`J@lByL!&Q;SiGYR>*>n#a064BM@^(T3pwixl0~`I0~ymod;}Ah>M8e&m<4_^W6QK&O#QRgNoc9Do?z;`C)k}'
    'B$l3TS2|vNL++-iQ?xxQH{eZ$2EFDm{eryQvXc)bA45~tB(W67)CGp16sb7%IMcErLo;?W*8%n@P#5RtV$TQ&N-1%h4q`e!;UKbj'
    'dh*?i#=)AKFw!onl?HJJgYwwTM|zW9cNA+22i9_@tF4@YJrlnMuOLQqfHFh2((>eMNM7h`dsPL2RI&uF2;y2a2Zcj!0Xj#iw%K$k'
    '5|FiI+XhDhdxUj^_VL;2QLZUdVsP^2)z&6#1%T_1?Qe~J=cv%zM~i24PY8xh{USMS3wBda{os|-&sQxs*ijM+VDwX`eqZgLY+T%*'
    'q=(-F8|2~PuKbn&m(M}z8_?&L{8a4e;a8?E|5?&Ewv%2y`e^|VHhEm1r_x@i+C!hJ5pZDz7`HPcUQ(YDAv&*tbb=@xU6pQu67$>r'
    '=^ROYFUNmdRAwDy>zzS6J_oH57A#jyj|amnvh$o2jn#N`HBsp8I~?q+Cz<NiSs897DYD)Cc7y0tMiCNX3M>r-+|?s(Tl-#0^uDF$'
    'XmH_aVLP(5r`&zXSV%Z@vf<=xm`W=jY=%O@cD%GW*Ne`fcw8W2dPP&v)_55UU;+K1v7wP7<urh=ItW~RDl{BH3OB_ToYD&~Ssf4q'
    'qm`SsSWQngLPkT^DdDcn<pi-vxUUXTgElAmDYWE?)iSY9+4A1`@uXA>dl3*aKe!!9<xdw7-X|s{K>D1iw<!$&g1y~GTvGRA>$V0w'
    'q1h?zw*Qej?6z$k=Fo^o^*PbrB-z2NXfAP>{~V(E`{U>L-yexbI#FXj+-CqwpSPbL|ImY0%bk-BwH8oRdus-h!^<L+4a809p-<(Q'
    'C+nmq$#YdUIb4#}C0YHe2s^gBWU5Q1x@4-EGF296fQ~a^rkq}uEV~=)>4khstCJVKq_j&)D`Wqpwo`>T(9Ah1#n8WGvP&krWU_w+'
    '+#{ZReK^n6Z|`73`!Iv$7MT-+Gf1XnKBaJ9a_7Ozb+<aBHqV3^SIMrDFCm@lY^uwB(W}XH4QswLOZI%P{J+1y`G1G^O#CgLl#)2|'
    '3a*(qdH!pX4~4h#;qEZ{!_Omc=9c;S>s7q}<KyS|`<wi6w-9G@>YKj(d%OLDF>Z35i7y|2{r$(6!(UkIN)VmeoPAivS8xB%{Jl~l'
    '9R|mn{N=~TPappL`Io={5ZKHgyuWACjN$ip>LEKt<dN1GACS3;@7ZVT<2MqQ(d?n4V|Yc!a^JJGlqq5VI+?!xCGdOZ_Be7b9o@yA'
    '1^Kxn{`h|Ew<`bTk#*Zws+FzV71<xm9fAXI&fxf};5w!p-B{Zl5;~J89ehEYGbjUvpz`6Lp3O~hDx^;5Cb=a47^7nPMS1_(uY3O6'
    'Iw!CqL#E@4aHQQ*u8_{E^&dugRAIk_>|3%7TNz7Nosn{DCCf<H{){9)Jy1Wz^AEeC#DyLf^28Na?enceYNmO~TyT|}n=Fg-RCO)P'
    '^psQajHVT|=Xc2=-~9Q0f3ak%&>@Ee-${=gvY<n{z8sQ!xxQC4Kfp&h+l*(EP9{Z37egi0-8U7C%y8b||Fq34BDh|A&CSAJmFn`x'
    '9ydlGk^HEWW_#hE7!-Ya$<@z+AITw^GC$*G3v7M;2ueaNK<<t7;!=`MtR50^@sEN#$@%%fMuy|mt#7#L3D#eTH$(356@jRGW66!('
    '{i>2wdVhrhFi_sk78EII<yROI!E3-|-HS|hIZL4;d~5IFgLI-!)@=FhHFq5q-h7v(x-8YDmtWO?|K~s4Xy}yb#*CfcxVRulHHjVU'
    'E6EX?Y9<?S_=4smJGcfK*oN1tXyqsQdxjscIERGkM5!FxKAEt@C&kK_Wq|g6ce%0iTH?T8P|%cwHD-XGGi*l~^s!}U1A%uS_kmM|'
    'IR$l!tpYdt^Gw=zwPk#jrLHJxuL9*P#(}J+pm_<~5$Z&h4<dERKHMt131OHbl3Ot}l$;)M(29H_uj9Gs_BxWJZ4Z=QuE-I}UyrKd'
    '>>ogy3@O|jWGE=cOTyCZGK89WRCV2)HDaAYDfQc0e9R~=WpJd#oA3iVxIG1>n!oSTtMe;+V@bAMy}hEZk1kAf=;g}UZBOMUGKhjZ'
    'E$gAT)<$8HZ(vhi8SURj4r!&Veo>p7Oe=*`nGwuSsx2H=x`g6&Sn|81d#03)4Sr0Um%8^>Sd;5;+E~zzdj-=mHd0H@ydIbUOHCnZ'
    'B{z6WFoE4SlDwYbHR4yO!NKLVVsJS<Ac4hPR&NO>awx}&EOW6t&vdEjnxY1<&1Xf*VR7&cX^p@XFRd&io^<`COdL#pl?_HC=m6XD'
    'vS*rwOC7;HGxXav&(KQ_XQd|KTKS%i`Q&9*+j0sUtL9BSB@gpAl~JT3f!(LDDVfn#^1Y;BjqZ$3^vCCDOupF_O1tVeRyFtjVi_hq'
    'rIHLwUjwKkKaxsG()Af*vBLmfiPWmeCq%o&(kw55+VD<-GDo1JWO;DCc?IWEJeiK@WGhaqk`_*?*vy<CsKe+i`pH760rY)ph<tXL'
    'ZT!bugQ=M&k}<M`5(4CJpCwBPU+0Ifk6&6(i9*<?+cnWpOSBj!_a>NeVT4s+=W%Gs`^ja<lMWXrrX^LP@k?JfA#k$)!#5h!wb<=F'
    'H+X9|EX&>9Lcg7g-ONpKrEK@vv}9w?OK!`qFa@FCV`Xzxm@ZhtQ`7l!>}p7Eh(_vCt?}s#_Q2CWO%K<J!%lRIINs9#_WkSo-7nj('
    'U;l&EBuONc?#)dXY$!WMp{&}&@-?qj@FeOz_?}c)#5!qGL6V-miw5%8LHv;fE_5P?H=SDbiqEn)>X+C~pBIzytx(<1;MviArX|*$'
    'X;0N3tpR+u)~AR5+NJq3r20-nqqG*$l31M1`nta&|G69M>hyHy)8?h75r%&LfX%&4_jZwC>GBZRJ5p$|xBLsQ4YOFISn_i^l&-O#'
    'ujK5#DVTV?*w{1{&f&67Ip1sMbt^8*$q5R&dB{JhkN4a?`G^e5<Ky#V@2>WJ220+|WF$w7AmA<g@AT@e1iv*7Jlur7?B`uA5c5$9'
    'w@v;Bbb+)5b66&3brZnYLsME;)%EvO@spMcLzM;VnE-KbC^EAZ4ex*X@$u7#KYzZ6?>|679{KuXv(tsY<7LL+nI-AkuM6@u2Fa4;'
    'W|ateTkZ;(TGpg6o7DDt=*t#v!&4vc306q0F?!qU;Cz%78C0H|F{$Pf3|%Tn(6&{u>qBn)!NJ(x6YF+=`NE>&Mh>;G)RPr$_2o;r'
    '7p6yoR8=_ZF5m2#kh*V|VYdb~PlotfLOd{xD`@T`mMHqfosETiS*=A^vdjv{YvB>;sC-#;rsx`bB57V@N%N}7fjgKa<vw!if;tKu'
    'sKmXdHaz=2X)cY;{4P&Jf9QFuLGM1S)l|bOche(bC)=2w%<Pa3wq|By`y+S%(L#tvbG;M>-L!{&Lfqv7p|*gd9VQz6QO)GCo&xxM'
    '`}cPH#jC_Bh6nTiR3Bjahg+#Ykpb!}ooxD~liI>_NhKqrLrR%=H~@McddI;}3Dr{stC#Ap>)!Don5hcvI{29QdgBPxH^!T3GcfeA'
    '66U|fW>Z^wllPqBa!WdYk8N3HBT|!OQaU*9Xt{23|I2}|gF7_uf)dO-HOG^*Te~8ImOS8+udf{7A{%x7fC0B*VWnLose$+A8zX#5'
    'qt~k(mkjjbf+vC$Ys3!xX8|8hzWWU+esEuxc$LnT5js?A4OOIaG8}NICu?_QP1TXM*E>%)07=9OdvuG}Xf)QDN_VN>m0o_<Ggn$S'
    '_CKv-D@GW7zbU}n<0Ac&!5_(8TF<V};~8=Hi>Ywu4h?$c4_Fc9zJ5cJqBOZ}_1cmyd(y_R2C`Fo08{QW-<{IIwZwVAwkDh!c68t0'
    'tOf498W?(3pgE?Wd|g_b=4Jg3pZvC?BH<{*43-}RyKSRkoNLL(f-lSuB73VSthfPZo+%>s0b8Fxe)|2%|G(3Kw~ut&_x>=bC~Oce'
    '?;Re|RCcf=R|6uva?LOjiPqFtT!)zr?h(5>lJ;X=WwUZ2l~^oNWgpINjxjtBi0OeiF^sHZbwS!MtwIt8G0d#U7OBZuY=KIE@F=x!'
    'aGvTI)J;M45SBU7Hs1h^US}U-0cGKH`Uw-5uHG>mm*|(#(p!>xCq*JeWdu>#W>y2b1O=9a4t32Usep1YJIPDe&LCu(V_KHX+Y0vP'
    'Koufv=b*Rc{1oWL&YIutXC%GkLa#6BFZL;|IA;~yUB1e?ElXb0(L5L~GSzb1>$=q#AZzvYh+fiD&HC|Ofuz(<p?!0w_DO2`*2<4J'
    't<JIAmNQ(UH3aBNj*7tutbflhUnfx}_Ff2o8yGcOWppEPR*7&Q`V?A`2G=DnR-G;uM%}q09t4|mtX~RfZ#YOuazPD=6Stsm;hq>Q'
    'H3qbcb^H)AIO;g6#ui9)qm-M8$BXCN(nAe>VP(|9+iKcb&|<qjtS)4zsMEzi|KYllDRpONU|c?xZ=LG+R5zvQ4~i*;-g4W@4;R^v'
    'jNF{EWIqELi8QDnKLu(jt_q4`AS9vw<`x8-#8h{mBey40dsERkVb@v45F*D3MJjgz8RDDJY15SmRD;HEEOm@RTLkeYK<B6YupFag'
    'v=Cwk14s5vA~OW02CGh4LJKf7UQudFJ+B}>Vrpm<#-<ddp%?m~yKR*Tc3(WKjI;wUmE0EqHGoxIgHk1h!^Xf-QlK!+Np`&7+_Ue|'
    'Zquol_jHe<IT9xZEi0f^nRxXoBq%yhEy7HSkEN*={Y^N~9Du&f9)4MfkwQTdNL7I>c9%T#9bHSO(T=cYL-Vnp^h)mc$?G=*SRNOG'
    'YQHnfeBBMQUis?Ez+DzqSAKmH$8Fitg;SJQY6`|n&gmh*Wc?}jrn;qDKUJwSxxTIjQllhNG#PZTFq=fcuRdx}mQ?7=Vu=5)9$<B3'
    ';hUbZprk2G_a`Mc2hMcn!dNKyR88OA&JgGW9%h?&gGalNys#AKb>bYkF9(4blv531xEh8~NjW<XS{$LKCe4SperQ0SNGAD4PMk!R'
    ';?+1BEFW_~K^JFJ<=Ay3A?3QqjvlQCNvqTIr{ya5(xMT$!7FyMi%S1ldL`Me`JhBpQ65ragiNF1*u%k=l@5YSQYk1u54*Y{2V$SM'
    'pC11hv8F_$&=NK1vyqmA>C{TNRPMz^MCm0Gy=^X|xu%LCq6}aSA!z)VM{Oe1Qs+VAZP7K7q2*%Zj{R6^L{fJ2Igw7u1_;;}XN2#('
    'r$e?q1qBnTzg@czP*ghE?IaF0`35SwI!0ulM!hErgK6OBKo5#`Yf)*_lDh$GVQ)#?dGa_rsbu1DMDIDjnS@x@oOpMSdqGiBj|JE-'
    'KR$l?@aLDG)#?w9rc$HkNyT6P>up8dem8r{cFgh(ro|S?ukA3MP$Lrg`QxYGpZx#-t2=O$mNd7jF~TJOqsY3oNUr5b3Va?r|N7TM'
    'mkgM~AuK(}F_zcZx-NWdKU5(W`>7q$%IuD<@ljf2{%IFR8#!yyv4|C_gsCWUD29+o0L-YgpnVAhodk|hu5}hm86G?fStpTyG1)6D'
    ')IkJvH{?|??y<eCMwDdEq+lw|n0EQR^#+v5n$*$qKR|MSNwY{r^^=Mrln`ri=>BhY{Oe<c3SQ^0*xb4C3~{tCxZ>(OtYmIVaIRZJ'
    '*w)3ypE2&~h(Se))Le^PLLG19M5Nciq=yX}|N6S0waJJ7F^q)B{>`A<^x!|YZj%aV*8t2wasN#9zfi6cTiT%*qO=~NE8+>Q|IFcE'
    'Gx<R$!sKg5n^CM{;;g|nQVpJ)p5KWAFFe#4Nf%lW&&ZS6<zuTH5&|Q3ojrJw;FE5yoNpv92}X->06T8LrgVMFfZZ(kx7AjkQn{7B'
    'C4w^W8r>R7DiVjp_pXK?zK%osy%r}YuMvf{$aXpn@Z%wQL@uLI1uE3P%d9#p368Qb^F#0@yHM(RTB1ViF>w>z)8i!NB<jInw^Zp='
    '7)gaAHx#7?Et`iNZg-^RQ=v)Mnj(#L!Psi;E#2{=esVtZspCi8i(t`(wQJ7y5ZP>BmeS_GN3^x|HnbjfsWo?}Xn7KAQ8<~GTXQW$'
    'LnzyMWGe})1-4RVTaK2eiHzBG*4+x&mdvQFMdCcJLEShk?{sK-M^jJvoQ8ICm8=h0YLTQKvbdAC|FpWy46!6t)=PWXL-8R$nhh=8'
    'T;5*KA!u<mNpVXn$~oOdCzYp-?K70*h=xV5m8+vIijS<EE3omvYU@cmyQgm9*%V}1UMXemFC@NIS?f|HHR^ld5~k%-C9xSgtI{EF'
    'Bdw*R!FUtZQ)ELzGP%w5M`CXYR*gd8;@vm3_)ZxVSd`tOgsSD}1LUwP8Xex<<KxqeezSPZrNh5{y3pR!{`0&=iJXNC*5Ip;X#efM'
    '#d=SB^x!1>*Y$sq<|^y!Eb^d^)zh2OA%6YpHmbthhqxVEORlS=Hp^~X;Zbe4Q^j>*w-b_`M#Ok=wFvU$L}5;95U=B3N>YaZLY_%J'
    ';Vo_<?B+08x|Z7}iECzu(W#cPyXL4x^I7hiGr+2HV@O?CI9w6(p~%7-6|ksGYC!2c<n?bAG*tE8bXO3h^#V$6!MEY%#8*HpYH>oi'
    'EyWavepM?Yhp!r4DwZTEXTMC5aD?hBq({oYVu4UcEt%JdR7Ix{<f|lOD7Y-S`q5Yzy3c=9y10WejKmV|VWbP4apKV}xW6m}A2UVk'
    '^7$*FG=O@tK>epAr>x%^t1Wt8_$g-T_CXQ{x%yV)V|5DM`|bj-e;pwFj_x(P^09wYd#ajHBC#E)YMVvFUJB*+!h^srI6AdK;j}2;'
    '-+1lL^-TQYGg8^XrW#?50zgY1Di<<$oF}+0oS2n^4yt$Cwnlj<`_HHpE~H+u>k@mF;Yk^aUqONXGmKFig2H>~Dy9_^>zM}{m#Yra'
    'XDlPmy-sqCvo+cS255*^Z{L<jrlC4Al(wwoGM&wg)D~Dxz#whS!jE090O`bYtzbR4Qdq9^?}<?~xIPQ@AF9|suR}DsmTyC6ZxpPL'
    '0|I<;_4HJO>o1FO3CH2=izh^?vZtw@9yg)Y4O{FR3NIsk=yc}o&}*tE`j9g1bvRdFhZ^=M6;7Ty(8T-g{|2W!*j<6A67`_e8G6OS'
    'x&Xb7H1Pr?)$w0nq2MUTSbOG}ay?il4qGm^<dA5GC-piYc895=76sDmmA7b>A!%qV8K^nrrz8LzB~ixVDmOWyMni@=VALF?y4+k`'
    'E9N82<dCtjo@B7*gD5cuU22sPhE5>wAyGY?BEUhRe$s;HyvAP<kL*x`J%Rmkbn&H<TBBX1w9?N?v0GM-BTEp25k<7nP-H`2V}ER^'
    'xcf>kjY{5S2Y9nV2`gBnAjj8euYJWqidtJr{p&mA!`PP2eHk?5`+L{dwCuOlzAX_;p}XQtMuHOdzDwa1bXTt2r{3?02tZ-dY<ARb'
    '#23F=5o*`vO(3-9vM(6<DRdJms38MK7kguKR5A4@X%1TP%54Yah++e=2(5B*A|n0uG#nZ#=&ig#|9~w&+7fNhJEGrAPp)e&tZ}BO'
    'OW1{=EeITnBTn&_x>^FBS34B9(BrOdq!v9oHs#k>wc8oGO<BLHj(#qE<e?l+W)6a%$(CgXGKRVi@k<86c<S`FXDj$VW^Tf30&3d9'
    'iuIsF9G`NI(tI(TbxE2WT0ZD#x@qx=mSw3B$THxy4f5vLa)idR=q<%PJTIk(6ic5n$gCRdXeC8QPM=TLPu3CU9PAymNLP5+<o39M'
    ';RIJR<frO_ac<k9?Qg$5`wur4Ue$bdMJFgQx5c9ghs8h+8=_-Qb+r3hN}akX@5Zx>y<m$J^EYm%`<``dRu-C@N!#ojawO!~wF!2*'
    'SWJr|u@Am(A{z#=YcYzO3z}AwJ%ZS;%whq2v2ZYr>J<+<dvf7mODVQzbtZ%xW#P#4&ngY-r`BAeguS2xBN``1)*-rKme2R$2o_=!'
    'x*~S<-Qv@bT-Ch3NFq0OwvuWI=E>zrbR220>#M4_!pWV?$ANvh7V+*Sxo>Me%h;xb$(B-ooCP1*Ks>AO0||M*PTi<eQfT$(*n<4='
    ';p1=RO_r{8lGgjXC0;Fc*cAYT!|^-dlr?8b#Rh4Gd|pOY5|(ZfpV|&-W4l+7K^8;87s}e=!X-NTqR^>M>{B29e|zV$8&`5{?YW=A'
    'IAaaOB3UAbYOByku(~O*B@~Q<AN~Gs@yoDblXX$Wj{H`v$jzGBjjiIoL`FtNtjqJ$SCU(DQH1E`u0?jcx%a2HTnIa8Ap52TqGeFu'
    '2u17waqU5y+-8$TDGPj(U2m46$fCVTmRJflobp_VCJ|WW0aXC2-#DkRK~BXMn|Py;Qt>E|taD&nM>_TR!tL-Z@jrijd;YlpW%vC2'
    'j~D;-K@^a*w>mp7l+{*xSu32V=ZjG3@h$&~>6T<wjgA_-q0Bi!KjLIE`)@k)Vt+bN8he=1(h3muj&+h|#f4Ikq&Qwi!(AzkLsu;?'
    '%tqL+HCvWp5~3%?QN*&#<T@d!;{6I3m-WC9#>_?KY-sY6TvS^^kB(ANq=NbrXouVV87im^N@QfiF;)`54YqIT1`mFmmNjosrr?Zp'
    'I&d&)srrNs8MbilpNDdTut`AqCNX=G6@mg6B$IY+7BZAI<e`|XeFWfyosDNAoe7ZhYpno7*TEG!+gAWMa`D3|*IWF%XW4sc9=(85'
    'o@fmvrb=^xW_8*DCZh*lXeNq%fdTX-^3P(`A9VK#hX7k?lO>45;j0Q+5}tM3wV36{U{rUqiJe*`pYP+5qC-loy0H3M5B^lmGi5bw'
    'SnUzN`Ck9?`pfi0Z};{dK7B@m$7gUMnF}_BUhU0@CiBa@12-Mf&y1ey(dtub8Pd@8?0lZ_G$6yeP?x#F57lR?di4@56G|+{J$SI$'
    'G^HaM)M?bsk}4GcY8WIDt<Di)`Z+64&jEqu`qJF4D$O2glm7Tu-oJmJ_@T4F-_)<2p~<}dwVD!JOTnZ|sdF!GQwjj6o&Zco!oIFg'
    '(Sb%y0T1afnq1qXup97{tTZjYu0z*4e917xOVm)1HrX0<E|$U9P|q%{@jAG!onCIK^wG#|5*z#FV3qCC3b?KtX5FAy1sIu+wRcp0'
    ')pfsVv~Dio){2#(uWAcJSNY7TGo)yP+5*BFUk27Ag$NhFc_14e3af0nMEF3U!fU<k!_RhK?`CD7_EFBgQfujol#!Hfa2n3)%ux$Q'
    '7wmL=29*zAsG!Vua!f??nd>>M6Y`YpEX&xNWk(}++eSQ4@`vFM<&}*?ghB^}fgKdxOp#7XE+o#BCkQDxnye}hDs;bE+hEu?K0mAM'
    'Yckq^?&*^Q61tMiFZiJ=kp}XxPMA9&TpCSuw+2JReLbN(4Dh(f0@;!qZ7qUcZdg*~uAVhCMvwmuN@;X=Wve;k_L}ZN7+L^qiyBRt'
    'WVL0~?<^~}O!!)!;EZmmx{gPy+`)2!(3X#7GttUDWZ{D=GH!CX2P*wY8|{x|k7Y#>r<^@i^xl0Mbz04-M#{0e859}`XjWu}_Q~Gm'
    '0`RvwFj^C}9T2A~0R*QKj8OGH&N1Fr&-BYdOC~vj%6>Pe@lr1N7u@|pW)Pb7x{CP+AF`?;9n&@a&)5d8xlw|Q<+4}+`8}?LBfU-i'
    'fzC`}B#DmuDa3SBPuz)n_T$w&KOw*L?di9V-=4}CY~f$~ZTIErcjAW*87|rTIi$NKf9I6%fsB3F%H!LyJEDK{)AQ3;Cm}ud_xY^F'
    '5?wDWfLi0}D*<+<tL7rWqU|i|raT5sDCJh5rExC9Z5pnLN?-Dv8mXbHUw?$L%uU-<J5m~&^?2rBGZ3ObJI4B!fNCmZFXS|mjSRAR'
    '>zKGH1wX8qGMtF4gKjxYE-e0aIm)gP^xoU+o5U3Do9bcng6!f#8Wo&Cp;Sth031Z-an4*cmKPV;C^rD+0-`Kep^vwP`g5(IC#!`_'
    '+jsi+biK1p3#d@40gN7sdHo1jpdidbqj^hmPbi1APECuI?3l5Q%+&O=+V$&Qt8>1lZKkUe>9@&h6`DSE17EY2>CIGp!YW+k`H4f!'
    '){yJih1XugE(hT>WhejA;M+Bh@v*2`BdqP<rWQ&s=-Xdu@2Y%+DZ5p;Di2}xsvS1fmSAw5s&$4hY7^;CWQx{!>pmx`e#}-Ih8Y_h'
    '){+DCUZ_4p&O9cveG{}0cOLhK$=Zdi`i!aVtvCHdcW#t<V(`ALDeh2`G1~9$(v&uMz2__~8^{yfnH!a)ZYBCf(W48AqIb~ve4Wbt'
    '2Mip|AL^Czb){#}`xjJYKtl|z5y-1X3yDbgeMCSZ$3KqOkW&~>w{_zsuR0(zD|)9}BCT$()a2_`m#^|slP^1z&cshPxCT?V-od{2'
    'E|K!g$s&v>z2koB);|mDz#_s3uDceduIZ0W>Id^IBMyi?Wss7LZimA(DLCw;uqmPREIF;-&{#)e5o!(hi4tBBUMC&sn7y;BXu9xV'
    '5f=7ut}u!vD;S=u=o?CAB_GIRC=4(Q4+OR2OR}s<15H+BJB%ZwNogAGWX)VI4J?%|HhC6%XI*8wK6kbmJn>)xvV#)ms+g*bIucm_'
    'qU}pvmFNT@96S_*36;VlFM<Ye_?j=NrRvf9H1o1o^J!hRys{cYQLTlZWM#IF6?7#*1+VQn1V38LE5K1`qlXab=I!Bg$|uiRpJRGY'
    'MTb80ri#uPlyW`SAQg7t(I~KRBU5FcvL|RXzh%2my1ES3cEEK#W#-bnp2Bff>b!AUrcQKsP%CoPuEIOR>B&%f&e4OopV~G(3Zt{C'
    'T{(gnmX$%VY*Vn>Q?W%_ppqYkWj>}`8zflHS?k3togex~51GCu(wp1wJYKtJw!jgZ?8~MaZH^kIdt-i6!a5!$`O0{fx!Y8nN=D|j'
    'FK-VH%9P>kyP9RNExj)b!#EyzGg4A7A8W2;)1j+sw50~9W@iXXTdMl0<)ordNFHK4@KU!8m&;Nk-Mi`oZg@aO58kD+dL=d#4(l{>'
    'o%M(;#~?RK_oSsH(NUk)^|^oC?5eva^mKw{04Gkc!nUPP+FrqY^RxcytqD<JXcqRbQ!GfqPmVU)ky%$t%M>0}mb>WUi_SuP1oFXJ'
    'jg++R7d4^6@-PPYC~kAx382b&LO~UHEC7@aYW<3GFh?3Qt$O%K(cIQR3V7BPfg|OcRJO{k2&6^CRggB|)toHl#G*Blvo49IgR4Q8'
    '&$UhT$j8u5^<Ge>l*N5;!9vN`^|cK3{m#+lo6IAIMzXhY*0pTWhIVDVW-M)o@R}m5^C_5M(E|mFf;M#P;>3%3eP=p%ppybLA`K^c'
    'sUneYD9f5oq6a<t0E8aVbp>0l&Etz8#aR`_Q|$ZJQ?zPYYW*>7j+FNj+m6z;%@+9Sy|3rYTG)tD9ZtOEn}+m<f9gXB{n=9qwy{Vi'
    'zM;!yierUJjE_O+)*3T4Tf4ZWWMLq{98|PEhYqwNgKH?VrVMgF%;6JmWsS9n5zocM#_JNH%H`PwmFAtlr(LS?Ih#o--rzQp*Hb)U'
    ')0YnaSp!44=~e0;dBP=9Y+7!kGM_;#-5}<hm*pL<gy%C?70C{jnr4b9z7?*TR}S-ZWPWlE=)k(pPa>9ZJyWn7Sa&&hL@f!2eLWn}'
    '8V%#n8M4EYn?ke_Y!tFfbB%c`IY`=35PHWMurdy(Y=Ow~Q6cuBFL27D!oFZ4X3>&mfr|<iP+>XS`HjQuL(~~P+sa!HGTq=&L-LLV'
    'lpPtQE~>#~a=E*2fj23u>>Je2JQOiML$k<f)p;4*+?JPf4T!M@7`_2~?F61E^+x%<4HcgdV>ElA*C(s$*frflVunpXTFl7KcE|+k'
    'Cz9|i{2I$3x<NS8L-Bm()8}719aA$Xp25Syh>AeAy=(GVwDj%Jp%vy*Y(4v4b|tBSVX&!WU#?RK@5rc)({8RdFP)JLt+@RxeYjk='
    'Zas$svcA)PPI9g1w=NG;vcO38VJ#hBI(z10g)SNQ^@{MZBS|vZx6GnBQ{;H_Bub^(wru>e`rO)6Mx1o<D#(R%hi!`-tF<~nu|4Eu'
    'z*8;<e=L+|6$j$Bg(-|D?D|cGmMiK~cz9sDHk$$REF~NmtNV5qL1ziFTxdnh&vW6wYa+lZ+0JcQqhqXo8*enP0&t~#4qdfe_+h6r'
    '$72T<wH~+i#y}3@XF}AZo!|9<xveWNE8$>Kg%OC`jj|ZEg`b1_>Lax}JYLGjgcn%+Ev;}Db-PQCvkvTT2T>-LJYC0-)mc(Sgki(K'
    'Wk7CuK*w-92)6Ar&~z1CZK=|%5QmEM^&PZIp?&QHUfrz4Q@z0_YxPbRdvye_o+v7|q=Jc!(R&Ny>~(XF+{W6a{`OQYy7%nxvVc1c'
    'RYZxKrY+p{6-4zoB_GTA%!%x=EkwwnYUjZSIbbIX_PteN)mdjAkcZp{NGxr~72<q1lK_L<7VBt<Cbzf=T2xRdCgfa@LyfmUN>#KG'
    '(5ej;BoowQ4b0JDxD{H7k^Fnh=m%_x4cBVnqvw5fu@(iR3VlmT*j8rQFh0%oETMvN;vU}iwrtJLKx!<>jg+WVa}CXKA+iX%kHM!G'
    'y8Dx_??;0-8gRGORUH~|Y8FTVzgm7^Rf<jfFoSz?!zD+WYN6(e;xgxAyjJSmzMS&|kHzJimC*koN>hDpIoO3Hb@U^*1fu`0Tp414'
    '<il<4O3|HyEPYL(MWtd*Y~10TGXu5|Ip2&wZ=2}6LBexVUh6rC`(@VQm5VCswNSKBw1Z;jm<mimAEu4V0fuOe!Yc{}XI*BX)#YHH'
    'c<)^Y-zyJKw7*fGKxvGW0ex7={3{PGq5n-e)YsscN#YPC?DYm>2cV*<#Wl<>1vf=gx`Fk#eD35X>!6DNJ{i`_o8P;s@yD?&RRB9@'
    'k*9E44JCYZK<U(JbvWn<hf^2|q=KNW-xrjA$4D8NIvhCU?;T~JpN*N@*mdx~yB6rb)Y-*hi(Xq%T3mqDeBqK<t~u3spf0oz55@&?'
    '=$hdQNppLxCz6aD{fYK**)@Vvkc~VLxqe$;nwQCXMAib7*v2NHe2L?(3#O7f@))FbVkaJ@GJqT<3yUY0_|N{7S7JOAy$Bc2nW#@#'
    'S>UYFf}~~p@$fso{)+Iih->9md}faYk<fz~sXKEBW`8ThptFwNSQ(Z>*Q|L+)Qx9;>O)hf_-Sm*O#O58v{+#^b@Sjq?C7dO6ZzBB'
    '9;N-kX$o?8s^3KYfzq;;4rh<zgnS%^;ye{C)w<FaO)%jvOv0wo5;&-)ox;i!-J-+X^iY#;19vh~2d9iyT^6c3dbLLdJ2kd*8L%F2'
    '@kqtdp-#}54cA|#i>coB$`#aXf2dwk!a#SpTA$G?gF8daKZ&&8iqwKi37^zoqnubTcwu&a1$y%OwsaX)63&l&muPUc67SZ?A5lry'
    't)yG#`U4Il+}InBUKMs9BSBtjYI#o&Af@4ya0W{@aO}tI{zk3&jmaSvlKBS0rm9r5yAB7c-nKk5wO~j^d4}-Lh2EV_o`e-Nlw#1)'
    '9iuD{86b)DXnO+gOnwurW%R+pjw(i>ZnrG9XMzZnZme>wY*jj3vJ2}HxmwMZsnmq0KMzg71Tc#)o<k<=QE~JrJ1a;AvkwXsSK;1F'
    '!n6&IQ?-p|wPa4At%`Ivtt4-jomn0JeAz^8G<>CdIl71ou|-*=y<7EexWCbRJ5y)+={$8<Qn8YV1x4bI^!xlY$(b{)ZTRnptUZMA'
    'TP2B5cZwxtFfJw0o1)&?eS94ilz}Zgu&zbw*4im2y>}`(&Tb(abfcYd&Z%r}w;~AzAC$CCb`)Mlkr(kP7Ot@(KNdT;W_4wvo6x?8'
    '^D&_2HCaIC60cg38J@e21f~HHfR>pvcvPfjXTpl9b}-9UF%HObU3LXME5dp;H}B_ko;BFk?+t@xVIDv`nF?}yLJDyX!eoluYj7#<'
    '>z|BE=q3v{og~@j#ue<EAKChs-GxF-u}{A-wsK8v9Gw_KL{+pCY9kN}__cS5C4FY0Y*xNbmXd=<FafXPm0naR%*z0SYiX37JpAg;'
    'mu<t(0Iwt&%V_k?={3D6?-a~3Bt@ypZj0dy!Xy@Qa@LrJ?M<>V(~7~&zJVf<@Dg~@k?QN~2@Tx@YE7wu8KDkm*FG4LUA1=rTAZNZ'
    '9kkU~<)jjy)0E>n+;jqT)`y;3b>;^~TekG5F}#6p>O&ajWM**|x`07(w&b!L@#{Kztv!o6X<9XaX>>;pG#JV><1{X5a1hGfR>|TK'
    'hKi;+%`iTW?8!`VoK3N12EM}_H70vb5w<OPB@rRE0E8UN5eC_0T;PGqmZ~}aM2VLc+k`Y>=4&#tgUjq;i#TMXx#~m$ro4CLx$@%A'
    'F;_;DBTOl|HY|g0l%x>~N6YNqStv>^$!P&H!%7b24DTme6w)5UEJuP}D(Q#l;^%icA3K*u4j!hD-MAD5Ak2so=-CHUDga1w{)aJG'
    '#;dP+dhL9$w)n|1QHgOwb9Je4{F-WDM?(`mV|m;i&<_3-bE9^c5R+GVMNhTCU{wMcIqK%$b2a9zznh<1B4Rma*O9G2WduDs?iw{;'
    '&r}B=2wv^uyi+f=^FfWrGs=EvpLD7@uU>WG$fx-5FnM1}4zIPRT`PlJDBKEjm|8Hx@0-Asy16$uA$z~$(AupWULEsy6hL4BpP)4K'
    'O$A%v4TSQ(UU$gA`L$fe+felm)0Y_vu3h{fQz0-_8g(e|v4oekIPPBN6FTlJ(%@|Bu6JC{O>KILbev!Jty7%Ctg_zUkC@*eboU$#'
    '#Da*3eR7mm-n}zAg&~!&x>~{_?4{#E@<j)Rk8=8_E+jYQg%{iGH=Gj5eQqE`%88)JP6^ag4xW#pN9RzJ0n)o13E#@Gf-XhK4jSyo'
    '+kySqb018VW(AJ2N<MlqWy9kwZBrXP&VY|S_zuAK-NxX_QAe=pQCcF12|&FdzI`XUjkO7k@@_w~Y<f3am&Wl`&`~W-azOJp=*p}J'
    '-15nnscBnPWRl`=FfFG_g|(*n2Mor_{nATze>6|ac{)`m@u}>+8sNK?UQ!0~bgbB2GFrJvT)){AA1G@~ey3VUk2QBPld4{BkZWiN'
    'kVpaj9*#nja<5yllp7G@l&1{S{6wfSYB=Hg+#Ob)s_V`;^2316zJcy1<XmeSy4_EGzB#>2PfX_ht2C*>6=N_v8kT*Vq<iti`d{(Y'
    '!i%aeT|QWGv(EE|C#a}b8tAf|Bk~jM{WnOtpMd0_>HwUl#kS$+D*vg$>3XAlp2Iy-NUeJya$H8;=THOT^b0-rzpFI}jsswu_?0gF'
    '##r;NR;^=G3auygN;b9msnQYAJOeg}0gypP<5GpsiJYZ!AUvrSB<h74`>~Ll0to`lK?Nb;NJxA|96@k2kS@C(s;rhMB8wb@#;<v9'
    'WHFrVMbmwqE?dS{R`gS-IAgLO3GHns;5UiZ8vTR|_P=;!ym%k{Zq?edF3_KEL`GP&i7oQfc=Zx4HfKxl#%kH<Xj2ZILFMlw{N9Ro'
    'qLKPIH?4x}V~5z}zTQW3Ao6)e6KDU{q3lLoRLCX~Txlz<R_vts)tLsGl&C^Ab%!&8hO3F1^=9hv(EBG<FnBE~R`)OTLUQ}IvCW*{'
    '&e5tOU+%(gIP$uCO%7tYx*G*N!C1W&TsA>hI$P%ijWB1Con}*#jrbtuXQCt}i$END8QF{|CMXx}FAg1Ni-H2`3rxd{7qp9Cz@$Ac'
    'w-!W7=l1r3#3268pPrw-YPNis_itduxAy>4`1+)_1a#fPBSR0Jq(AoZoS}LKnvGDz&)g7lKX=^y&}7FN6&4a*hK|znou1fwb<F*X'
    'blc9P|Hnth_V_Wgh);FE-j9h6rFJA8EY4D}@VlLqB`U0KUIo)Y0?z#oAKsTeleZer<TKk_03vrKU5;E;q$Plw$?dAiP1}a|bl;-i'
    'mtlvW%cY1=#s<ox3_o)71{Q5-QXU(p*DJ}QQaTQo=WX{EPImf71_Rj;Ldi@ZO^yw|xVu^p7g~$WT`UxS`TqIKr$7Jp6zOb}A;<=V'
    '!s#qEBB;*`LL7pbs>b3V)TU=g#pebo7)MUasQ~sXDz}A3ntU;gh)jCoE6w^920RAOA4Rc~Eqh@jRyM&KI@11Gf4uTZZ)Dr9reCJI'
    'T2@M-`yiTw)Wy?@7T0ZO?vjTfj>4)?D?FQP>>?ugE6IbyJom7sy^w|Hpt82d$`e0d{II+f5=$?aD;+PsA$L>MDcT-Q?qlN6puagx'
    'zu46q=%Uq2ZWGp&HAyVRDRqG%C`BqxJucpC$k2@4%yEF-3e?5<rPwn9f>KJ{rj3}6PdJDyPQiTlqH(b1CXBQ<bEQ2aOC14;3DT4F'
    'x}#WIIItEw^(PvGoy;CS2CpDSbAU2Kw$k$CYe-(`YkN}#fmE^tt_b2<G)IL)?gMm=Qf;&8S|lLfl5HED2<#Eo4cf<dSSQ!{A8iEf'
    'vgv9QwgSNQ#}1dqp>tH|?W4srx+Vm}rhbu}wgtPZr+)BC>6fdPJ8UZn1u%Nmx#z20lZ}h}v-I!>V1Yb7Zp%*zaQPgRz5$(W$*W>_'
    '55F>X`OlKRv6b}mt)CX~V3Wt~Wh(8Jsy%d7jerX)z_^<k@sheqgy_5l(g~t)bW^$nO3ZH$r*kCry&V5-QJHm+t@j4)_#CuKSg_nQ'
    '-5w0H$j)<8G*;u$)kLAU?{KiQo@A<5XJxpVq{#O3+YO>q8AV8lDX=sUa9@wKZS8w0(fgK~qrruzh3&}Jo^tmkV<F+t$%d1&VJfY>'
    'u^9>p+xF68UoYB+;&Fk9=@m^uTjOOcfCcnHV?!fF%4q;!br87tRA|_O6mE(wIHgx!vN|9JMk{x1v6`N0gp7u+Q^I|j%L!tU@K7D1'
    '25nCADzxN@)iSZGY<chUcv7l`y$A@IAKZ?l@|PbFUMD6cKzg64w<!!i!NKYy4ylK+bzcLX(5#ep%l||jcHg!Rb7;h)`kZKQlI&ns'
    'G?zHce-6?7?di9V-=2tDI#XjlK4bt(zwN#}{jLYCmOCdMYb~It_SOt0hnGbt8;G0ILs#XPC+nmq$#YdUIb4&~HCg?&2s^gFW~ytZ'
    'x@M}GGF296fQ~a^rkq}uEV~-(>4khstCJVKrnGBHD`WqpmQ#f|(9Ah1#n8WIvTG*0X0pEq+#_E6d^pe5FYjPO`#6K;J~Af;XOK+E'
    'T%~Yda_7P8ako07HqV3^SIMrDFCm@lY^uxs(3{D04Qsv&pX~Ko`OCk5`TvI3O#CgLm6AB|3T~M<dHH9OH-)$I;qEZ{;Fpm%bIbhv'
    '^HqHO{qt`h4;T5<ej(20+%Ns{zq{R6jB%6eOnm+Px4(b?di;d7t_0Dk&BdE#eDx0h%)h^sNQc4kCV%<<`OBw2fBfZd-vu`FNAK^I'
    'G-LSvox90S5qY9D#s_3>;(PJl`uL5+Wi)%}=ontnsoeJ}EoDmBf9_0w{8Qlf!s&5jUpl#pJs;%9iunE8sb^LG%M;)2P^nh--EPSK'
    'U~Ur}cyk8FR|VHG<><!R?vT)#MCsrQ;+#PlC<K)c|MYBbid`YKJ2%NC`P&#3(=W>Vub%Gpvvp2jMTShLKf;N2OSwWitJZ%U<xz$G'
    '60&c}XV}SDy6TLS`&P1ybnDMZ^4$aVQ@nh$D@t7GW+6{pan(NGcSy}NubB(3a&wbqah|HKg_)jmDxT4_g7*BbIphz2zCZj}vaiq~'
    'hXmhAj~ud~L%O~kl6$$nS2RDsM>*S!XOm7QMM)P!CDq+G6^zVq-r@hW%`77Ly$+h2g-@00^2csBMjw$p)LFB=@FNCApMK`*=fIET'
    'kW87!__+nPzJ3HHp%x(bMtX56Nhekhi8%O2!JXv%d|)BNaq8AL-1G$NFT|T6XZVUh)V;Cf!tQ=lNh-a+!2lR2Z)XdNl(h0242j?|'
    'V6yH-rn;P^P!YbhkMKr1Q73D*{Pvc+jtXzS>!-SYs%tO5s{j7q|8S?FQ>Gg;c7EgHf*{o-cCfD`TWqSCY{20Qnvd+@8fah}UaO*&'
    'pXBcu9$v8z3Db#EIktT=VTn(QFJG1c+WXz*#?EVr1Ajq5Qxevg0ea4`9bwSNmYod*-htc)P8H@9)G4+K-006UY2VeB@l}?(qNKeF'
    'l(QHIvYLYCXV{KVC#rl9sY~|ZR@q$$!xWL+ilL$8^oXNY<O_Kn&q24>mLzR^p!9M@j!-^5s)}>C0ckR%aBYyGpcpR+OS9_`YUWYZ'
    'ZFAO$bqb}_Z)<UxQC!O4NQpP$2Xt_I3Q9G9-=#<AH}=MoY`c1UMPDCXnCQ^Mm9yKP%1vYt1y@?uLvO8(!X)3oro1xRzm06tN?HA)'
    'HaD483a2t7n4eTzIIMID#p|%-cS-k5DH|KSOq-Xw_f}Yw>u}mw(2jcp(=j$uOZL1Tm;g&nA!#KycuO#W-8YiFo#8d&N2tNU<*j0H'
    'IXxhO#avb|2`6$W$BHa-vAfK4sp*=c2C&U%Map4u@C|8=z!Wd7EF+$E{iRGCOn#LOMkD9|+w!t!nuSXp!8|kc`!&zdOEzbvCg586'
    'o{stCbynMQ3LC5DO*|zJ^EZ`Iq#}Xcr?4rR(N*%jq+pHij8F98b2KL3><Xn_^&6|2dw;PElb%vZhNW)-)R7-ar6lS4jIr2Z0Ix)9'
    ')#MYR-C}8$mq2ZJCPA4a&{ncMxZb^ieJP$yM|83kyH!aGCsk}__7BuybQb+&q0|8SJ~c!>yUaHJ@YY~zrio;XETMz|`Rub~DdFq<'
    '^!)U-^^_=teY#&04YfpzVRCPR89$7$3hX=%EqOn=40+b!;>@(9N;H1y>m~$F4j+7@F<pzD-gASucEhsV*)8<!RP1I>iYsNi&!#0C'
    'yI*oyc7-Vj{T?fuqr!B-5}umQmt#jmazQjwmuihqU$6#V{%Lx+PHc9fQ^e_({vY3-Kkk3oJwN{gt4WebDBYWzF4$0Zj6zwphvjQt'
    'tKdb{d+<G}u!wciq=F<pdlwDlv4i*{30&w*4sSZO>J^`5Z`3cbo!&1d<6EJ+pTWJO`%Fu$JJX)3KUxF$POUFD{k2Q;XGry(hDK>E'
    'q9w67o%MBpMgB`C*463h&Zo^wO(P8b`~jPLo9^u*!_ws;aImG&VsH5uUK?hyMzQ2^I+U)l$5(Rp-W5zde%jbH7S7?aPC4Ie=5;GB'
    '%gG4}x_HPxsgL*EIr)SP%hS{AZEsuqK7%E1W-^i^MiB6p!*_b~UV`5m2Oe%hKlbCS7Kr(%gxe<n09_z$!5o%}S=|IMcGHyBRdxM6'
    'Rs5u-!cb+wdL}^J8;Z<qMZ^1FzJLDm>CYc8;@fwSkVn4$*z9!SbNrk!c;S<D?bikQ8iQoXa<fW=ye)TyOnug*Fq_o&dg#X%F2i$|'
    '_XI1XzA<{*>)?Ep6&Y0Sn=z^85)54`NYJ)bu<JuE`@zB3!5!;XfBA<+#f=<lVW~SSTI$O`;X#<52vSwytUG+OdqV2GU54En)I1sD'
    'YYFkdFs`7vk65DU6L&Tiu4T0rUCC!wI9?04NJr(%qBBLu*fUA<7E78pO*Y)YBq{fiQy0`x;6NqrHMQW`_epbUZ02`)8v0|;Qw@6d'
    'VXdYbR=JxV2|L-w^kim-bg(ru8`~eb^N$unJeupJFzBW|>@(snR|vHQ9PKdC=#Oe9KkGSw&maH0+kN#av5Mir{6EzPnEvKgDo|vA'
    '`bsC8KIx>k@LW>K$moz#CLRueo`>FX@G7Btis0*|`s=!PJP2m00=o|0CjPx~1nN8E$+Q_5`cw(?uVS;QExpNmPI0&;oxjJHtg;cQ'
    'Nir!N9Cx(bHaY+0z}LYQns-47=AD}DN!qPlkwHryaLLzK4sel;I)B7~+pw_Gu94Khd-I(UKBdv?RgOyr`f$M=L5ekE2mZ5w4<}#!'
    'h7>=zu1ma1=gJ5jDz%0xQaKq8IMkE1yRxS0NZae3ryGDIVud}r#A`Gf>rAD))bC0!KkJ?=tsDFA*0C=}7=6Dhz}({^{gc5T$yHj<'
    'uFvBcarcX<aOVyUdgTMGh;m=QAW2c0+_HLWNtfMeV^{;(u04P$_nGfb>EK%8JYf4KoEmm?-QT}ixOY|vIi^#5Tf3PI1AEWJL<yDU'
    'T}k_>Q|#sXmE@^`Cash3WxPE(06_Zf^OwKB`2Slg82Ln#`QZM_g><zuDj@wFy`Y-`C0My|)onRxW(2rdX6q`QYc%?sqb3U%be1O9'
    '20@!FvBYfnx}#cZRZ?7bH8pZ@8f+k(#p5iiY}vkiT)VA>QYJ2!v{MlQ42wVO;80M<^lcZ1nMRE?+6;nWX&{TvP9*oabz@cZO$IHd'
    '(!im#IiwQrQ&4%N=whTt6`S!vDryb(qfG3#RwhM4(qPe_?o#JXY7Pt8sSc&*Ju0FHsx;}%%W@n)@>9|xhH_#dIx(H4z(|R~bi(82'
    'Hu9m;1D0%y*BEMjFEXpLQkm$0W>f+)1Jmic{{3tc)^);uUhYx=P=^8waf(!$K$%Y&#IsMzh?Q)hdoT@f#G>3?a_Y~uhPucL$6$wH'
    '<HOtHskAi78|A4|#{o9Y%tA{-?{k4g_6mt7B#}tTNT~BS2Sw~yXQ@<78NP`<J)jSh*#}o-Oo$egX#9X&9N|?JEu}ZAyl;ip=bHQ!'
    'sU!9~cN&#Oiu6%%PYyNGdKZGF@N&V4IJX=~fC~$^Ho$g$+=X;Z7d6Ur!DW!aM=39QRX(TXLQWrErj(B!aQ*JgHM?VHWQ;+5-+=v_'
    'F>3mD=nc}9WCdgZgB{PMR+U6Zza13ekv2Vv;<3QsmGsw@<pXMrq{B|c?o;iUIhk3|BvN_kkL4^zjOvK2Zw<Rr*<?>c0uIytkyF8g'
    ')(GLDUh_cj*^*W8A!|F9;DK&&LO^0q8M*`HO%mK^K}Amk<;-omUgmON;c#8wEDu977@v_tYDKk_>vLy5n?ruvQ904y(%Qnvt$lK7'
    'NCibI@<dL*6ItBZD$=mHgkuiJ@)jA4w5%#g*tVzkWGSg=TIgj~+OyOY`X#4J&DradMqXCuL0&CY2uP13A;i`AK@Hp-U5aQxpdh-c'
    'C~H6(7G$}BYU{Hj1kcjvs)$z9^m?b1c$D71krZ?J@r%mEpm^OR<{XpKOE^1_E5Bsusv5UQA;F@L-l6hOE>6JH2g5X<=E`8o&n9lB'
    'j=dFJMw;8;nN4nqdkqF1ypzgo5-Ly{UxgmUENDWw+nH#Yg~vBJ7N!p#9DXphzWKYV`=cE%f_>T)me3a$v8SSS*`!eIg0WX!&weG5'
    'fhz1dX5!@NES(bHqI4_z6-`RuQE6d@r2E_M%hT@*-6>OPkMN27*}Y~^LkB*h2S2|R&2X5HfQEWrq&{=&(9Z;4HzXUBLtILtesfnZ'
    'zQlYowv?-l+ImvD&P%2wOj#G-n4*rJ(Z-3Fv4S+U+e-a}E0%vzy{nQ{vR&gM$+jg2Ad=B#l3$1xYPFD0K(45z*=H?FNev{=9hO<i'
    '>HL~xSIjTpKY#i3=hq)q|96mrEj(^>T6Hqo&Bl=AW6}Aqul={Dr>{cWT;Uled{0SY23qN)nn{7Y(5~sD%%^BSH>|Lpbuvl+OO!sM'
    ')QYtZ*cWbAhS;${0Ni!zEPU33&h+Ome}D1+|I=6*Y2O78J+Z)C80|UkaS5tKH>|~n{ox(-b@YTAbMi3HcxsRvMt)VOcjvUEVAFo{'
    'x%|*G{bu44g&dO19y*lrLG92ixxB*H6N0D*V7)_-{6Lb(Tcn7w!Y?}&CvyAC@~aHIL{bkq?%UeKuxt{3XHz4-RIhE2#k^qd@t|We'
    'mBS0-b_tj9KXa317X-k4@^JXax95-hUv|&W|2Q{cu#TknIsrKfVrJ!I)(~?iTsGlIk4=n!6knhI$1rt6g_@2l$QSQK{m(nnmQmQ$'
    '07gY2tt%viSQvq^<67{GhT$<?B3>gCe|ht7WkW^wLrM5z6pVt}*UTDR$`RXE6nJ6tsgZP{We|<rncZG8x#1|La9dgRS)@Q>_rn+r'
    'Mz;81;f8t8KVB%B%YamDTD(2iT761ISNfI+%D`)MYAC5l9Da+rx?yGUh=Mh1wq;?#pesL>{=pRp1$zZ5)IIZ?JncytiFj!^vI<cR'
    '76~#tN5n;8pf%_8IL%#3C2@H9mZidx6G}1=$(+DyA))aQEG>3sUyCwgfFaV*;Mli7iR$7-edm1UQ^$|G7vYC_=5LDaA+p)t!F8JS'
    '9AP*mD^H9~Ss=MH#j3dPI(k{nu@DWRZ0C`!B(nS%AGU^_NHt-C4}53cseo<C5PlSD=8+KW<*@%!Iw6t=_(I3VmSLCF<seHf(t(dG'
    '?&R%1QmtCFO)CAA;oX#!HkhiVo6Fnl*#s?KDY0-fG<0<bom8GSw$D%sE2{uR62=?0TBAFsAXIW2R$ETAff(H2{-uV2_rf{QmBhCy'
    '(^-n7rgE}V>B~CrDv8a|`HSD&8QRtLZU!iT))Equ$!)Gb5_?OrVv4qFL#O4oMJ+y42K8fPrzoMSCwc=p><S~abI2szKRvz7=y!|1'
    'xpeq<NEbS|+yCBgQ6gvIf;IT+<30Q6Ek2Z^ywHu4>|fXaMVhOuud~RFI#y3_N{9IMU$;>e=HA5Z*jn<tN@}z0vK4OChBH;%%zHN>'
    '*=fYG7FUZPcTR`$u)%gB|1Tve!+#*pB%kmSw-9!7m@Hk(t%pp0s%7l1Icm{-mb2yzu&Ue`QWq8|5J3*2VPTC5SX3r8pmZMc__qog'
    's(Nj@D~KSj2PE-HRY7`Y?Or=R3bClg3DHBVIX3;ORz?nAHTtPolBAsdGDX4>s;`h<Mgt!UggR=;yhfxdI)xx#B^g7gzm!DSCV6Nx'
    '@BgTDvBSYsF%~|`(vRi7bg~cbFAK}<eiS3))K_Iqq|3<yeuuC(<*~IcTQBC*9fBl|a`nB&$Lbuq_rn!l|29DQ9o=j8<zxS*_Ea^Y'
    'L}EKo)i#TUy%fstg$IFMaCB;e!f8>wzwy|e>zVk)XQZ-&O*O(A1%Q@3R4!!h*iUd>I58^+9aQgkZH@9!_McHHTu8lQzf0^@h9_kx'
    'egy^k&oD-92nz3^tC&_ytY;o*T&_AupRtTM_ji(OoUPFwFhE1RdH=pVG7Z&{p|oWsm+5R~q_)6n0tRVo7Jlq<1xP2JTLtUEmBMnR'
    'e@~2}!Sz|F|4_yDc^jh1wR{^od!t}|91!4(tCzbPTz^@NOE?Z^UpygFmAy>$^tcJFZrEbqP<R>PL+3MZhh9@X(T9|2ufw_eI@GX7'
    'sc`btfhOK>{WsX%!R`t?m8b`$&d@6s)&=Nsq=^?GsgD2l3I#_w#@aK-l<UDdaoBRPC5J>iJgL_Ku{%r^wJ4Bgue?R83`s*{$w18^'
    'uaW?8ltdYatK8&-8Vwohh*5Kr>T-8=t(cE6lS9VBdXmAK52C~vbg5NF7&?Kx$3*pTjsORR`dJH}%Nl=0JhEdA_5}9F(Z!caYK?Z4'
    '(n>!o#co+Sjx0e8MikLPLy-l2i~X^s;_fRwG%9(Q9pKFdC9GhPf^1)-z4jFcDQayg^{?-c4`WL@_hZnI@87Gwre(jY_HBt+3T=xs'
    '83{@__$`H3(6(H;Prcp~5rD#^+3cuWh(G;hMX24DH-XTa%l^U0tI$QLpoR==UF?a?QN`5nq&aBC8@C;hBZ>{gBDBiMiHP*q({O00'
    'pr`T%{R6iAXiKy~&xn3AJ-M#Au*R99E@3|eZ9(8r9C3=b)YTI3yxO6-g>H9sBem$(u_-^ks@=}eWy<<hb@X%TBM;?pGIJ38OtvgD'
    'kTKMCh+i@g##5)4JzK%|F>@0h6HwC*R;&jd;`o$vl;(@!tV`15(DFe?(@l#{v@A=7K$ZcoZICy|mLoKlMQ<tY;dv=Nq*(ftL1xup'
    'M=L2ha{7F_ezJ}*=V0%kMY_VnCbz~73@5mnA+M?n#<^{acEA4m>Ob6Fc~$e-6`i5L+!v1~92NsPY>19I)zR*2DRt_uyc^Gc>;+4t'
    'n7?s9-S4bpv9i$IOxkAOkRu_-j!m%B#bR0%iGA>O6WK6`9g9)iT+p<d>=DGCGK&T9#lq1vs#iSd?8$|LEv49=)tL}(l!YVDKdUsT'
    'pIUQ?683@)jA)!3S%>I`Sw7!~6Ih5%=!n?WcZ*L$a#i#CB8gns*-EM<m?xJf(Q%}~uCJ=z3MY3m9|zXuTEx4T<i4GGFJqe$CR<AV'
    'b{4#41M#fB4<zLMI(4JYNuky6V+-=fr_aBZH(9#YNm}pkmUy+)W>)|Z4#)3+Q`Vd%6&s`#@_89qNm#l`ylXq8jqP4R23ZUVUnpyf'
    '3zz8Vi$bS5v8z5kKYb;+B^O1AZthxSx0`!^ddr2dg9fs1S|C~m^^H)(4iMKKw8?EYX_T_SC)xF8DT*xGn`DWlV8bcTg=i9iRUS|U'
    'u=<U23LE59Y_W+q3Mmzj0?9fDwsoXak1yN~&l3Oh$G7K?`(Jj?&;NMwUmrvPNqeia^Fmo|rI)qBiF&>Wl^);nub6I0R@LaJu^Y;q'
    '6Z9iaCbR#hGcWe11EsNtDJ`u4QSVqMX;xe)1xbqIWi;HC;y85G^1^I{{aUkS873imQXEAryG*VVf-2sxfN@z53}MV%RL+JbKgmV4'
    'CG_Yh6-6qjKY@0*-JhX?+Mq;6HXLIm0o-8wmTvIi$7xyf24xD)NT&k_la{Ja*pOih=l*#pHwc>qly4HVCs`pVa6vL@*JdF@SwkL*'
    '$=XK%PT1LaCeoPzIltBlFmxSUp|gDjfFl<_ta81@zk8Owm*&w6IOU1fP-3by7id<e9bhtg;Du(Q*cTW;Un2i3R{cSDpKu7Ul{Q&|'
    'I2^vJkR{<+$6bqAehfx+C!5%*Me_MR9w|Dc#HtIcul3+h)jU&H!-mx!@tg1UKd-+`PxN+g@8Q#DG<bXl7m~SPQ|Q&+jA$~y%sX(?'
    '5&g{QxgM=PrIsNLUC++v8BYT;tP6FSEBsJ>rm9yj(K4aLa@>Oln@v+Xl0ltD-7Kj>@vnwK64B}$5vHHB^7I@KSgtS4?W)r3kv8d%'
    'f93uA_lX}m3;a#}+8LV6>tCxWv9%OTx|BNi;x?rKfa(drbR_KS`V<{#)D-ZL{-VjXJqo)4PsvKt;_Etet;3fLL%c){1!<G5LFZx_'
    'd=2&N(i*RW>)Pq%mP#Lu+$OQHUk+B;F0Fv;x?$E0dR2gt`B-~L<yT$zn?~#A0&cBX8TzWWFm#pAoH|2_HmEHitnp=FJyM8p@tX&-'
    ';i0g~mP>>W1S-7N%Rc;U_w{a825KMW+$*(~u1Fb4=?16atj-*@V06Jw$7fLa@P!J>d?&|5G@rSi!#W{P+0L?zy;*iNVz+I?10{bL'
    '{!m`oI7BFPP#D-j(ajX;q~t>4OnHKkf}_c*@}NTZtF;Y=edF`9%DyI}4d|XeIUu1c$^3#Jx)Nz159@@v1Hz@zM0aa2MBLXC%EJJU'
    'i!6{WxzW}l=;ekbRqpCpLu2&#-=LI6cUQKWGj6Zx9)zI<z_zH-lu1@wM*YsRV#|cD<q6K{ma6M`w8|YUCkSo%ST+-_+(Q;VxFX{w'
    'hkKyXkF?SLNcLD(6miPgQ$_FHr%|WXoNA;TtD8Zgk$`4JR%oB>T`mBBs{^AoQQHA=suDnOD!~X<@8cZfZS_pQ9JFMTBdF|ma~dz@'
    'l7GS7A7lohS+A>@fAArz8qzUc)BlWZ;F=pH$XG6m1(4t4N;uNn)F0@~6h@NhxSv8yH}%AwxMx3J&GQrTOW&S;`}pmtjKLQEwcmDM'
    'o_;5O=#b%(y`Mw6Tk>~K`5wsFhpjxm9lIm?H$Oc;eRUGjV}GB|S}f7^!UCu@p1u-bXS!-G0xa6jqHfA#(1cQM1zH;CGTf%&nyB<8'
    '&#93by887;7|YzWJ+&jHp;?b-4mJZJ`m<xKZwaWTGWJ4FBiYCxo41aMn^N$@iYdd1$U5kj!{ox^Uzelo8bR;9y}n6I(Y~o3HZRC7'
    'E~HVx2^31DR0+UAWFF_tMPqq!fsJwlU@joaauxb`Tc|(R3VO0y$h3W@e^1vt+q8fRr5eEKp_tc?fCUP|EHs+8B=>}JSnJfZSjmnV'
    '+sI5!KdW88-nBaCYuaYII+1>xtX84vQ#bH6Ynk3m#V4%7MV_BH#B2?@j$L@|HSBT_PE&UBFAct3;}{={nl-}O4sL3p^n$+qmG-X6'
    'N0_o(g{$%qR<GJ&Q*8+b*Qr`(_@XwE{zRr|jkoS|lIq87wPBdCv0*JaK<|a>Gvv%;BHK4X3vuUhZ<wrI$g0nn+TME8Pju%-nI{JC'
    '+nVAIB^jgr?k-JfgV%e`(z1a(!JWBLN$OUjUlcvMkSKZwjnCJq%zwbZ(fpxaDPLE52EBhlRR%P~&>DffYP67ubl*n=6mtCIcnvv)'
    '@pM}^Uh=8~GP9z0x+T);_DW5@UUm5@A2s>1L+MQXWP@ukb?Y7Md+!n{&zvm6h|)Xmr*8eTunsIDjNrO!Vd|Rx*ra|i&obhG*i!~6'
    '$>?@COp}7cP70e6O3#wh>J5!`Bo?98aGxmQ72$Q#fsWZbyNad@4;Eoz|K<v#Sh9lQxr)A_WLENlJchymv+zJrJH8~#nl#X4MYh8@'
    'LYkDO(N5OP<<h`X>0*;-v3J&0rt5QOo52$gCLlW~ajuG~%BUlO^)K4K)K!U20K&mTF_=&(Jn|xF0Ee&nl3J=By-zbQdo`cdRm&@@'
    'F%;EW=t)*)>sUco5>)Woo<s1X#k>L>g*JK!k#61|KBs*0ob@@T_f&M~LvO0+oIxqqa}82q2Of<A3pX-V_9=UUM)O;?`=qPOU~LCn'
    '*HdOL&Fd)~XQj>?r)BCycL%j1SM4giGn}3brRN+yi2JE+)1xpttJ;+#h+$b76w5XRt34H4qy;MZVOZv4y0t-q<(#!%%+mRxfAo;)'
    'Ya+e5{m$dHdu9t9p~=2%s?p}CVY)ZwHzlm&QIfBWXPLWA#i?XuUi<R);Gj$y&c3Tz2HVp6vM`L}fj1*1_42XiN;Vz3szzICfNFMz'
    'u(YMBpIS~T`h?^mwgWG9+i<xoHPXGSKH!E2Wc1)&DyvswL*cMaBiC7v$Z`yFqjXPNN)jFQX<eWD$IY&~YeG*aSO#$71S@P?`lRg@'
    '%r`&luilyv1%_r}|2oBj6#V39qaB%brL;`pQDwP{F23k2#77_>tkp<K>wZxaDl89UfRExfx19j0j3*RSfyV+s>7drHC<k+-G1IDt'
    'j}*;q4Wxi)T@g4^zDZ@P+=@V2L|g@F176L^Qcf&dBRT7mXgatWbopG{M2~z7?NsjtWlCAx2Nx`qd|hA5P~YzyUB1aYVrV3L8)se1'
    '7Hw!(#%spXb_lO2!aARV2^Kw2peSfVw=Pb+sMmL<a|b#pKqJy{qL(TX`G&Hr=_Gp4qYpsn5nWfX<=Q;H2vVF?Q9Q-IZ#_k;rlr;&'
    ')8<HdFR|??UE6GdpWgd=&a8!v7}ep#TfS*XfB2_9gwUTom0%l-Wa1mTT&6fysKodfgl?@dQ?s>;TS^uN0?a{0>vQNpD>Ar-B5TSZ'
    '_rn}M;a1jIix}}-Ol-U^5vp9CT~KM>`Fq->8lSV7l;RC;BY8c=6E=P6@Sim>l$&0q?vW>4BE_cVHY)QO#L^97zIj>R;YxTub5)V-'
    'P^oFAh~it}s(IxwPe<k_=YS5Z>-;2Q3D+|PyMc9=b4S#YaM;(w5v|cM4xJ%8EV(H}E5Sw~yENCBw~~XT9R;CxoB=E2aLN{lEFTqO'
    'ANm5PEGp~^CSn#XSr)jcPyrQ|vz^~K%sxb&(X*|*^&ry?9yKKISU}m4LF%F!OeUAR`xbbUvdX?e{merV^D{JyoK~He!Od-XIoE&~'
    'Yk=V!z}HUTiBfNr-`h~}2{A^q7kYiNs*YXLJtSt>1f<1`>}-cjpnf6=&%&><45Ax^Gd&c~XFh%YwbL;*gW?%HER3iKWZSzYk3~!0'
    '4jo!yF2&Zf?`2n#8W;wfO7`VCh47Ay+BogzYV*<=$<T`1&(ep>b?er1I3Vjg?dK%ddVcHjFeM9&WFOYj@ujn8K33?GabK?pA3KsH'
    'lYPr9nlnX?H&3Eenr+L*FRRb3J!Qm67q5a`ICt2#$gx_h0~FgsP6j;Xa`4AOc~)^CZd;hbc*3sVRA{-PE`^5&wrjH)AkR|5fw8)8'
    'XAyLkAj^eTwER35{<|gutdi~AmNh!Y>bLPm^C|#W%IDBk%Y`3yI&(aBa8c`VTW<{HAbuu9P1^Zg518A!^0E>R7F8I5xZNm=QCs*q'
    'xUW7^tHa}^d`x(O#oy8jcTu;y^f>Fl?sgDmV#(8W3|XBeRYVvz{96X(mIrhUw}W8YJ_Aix!PS;3%?fd-IA7mEs}$PTPT<weT0GSo'
    'e6m*WWU*IA@al=8VoNHR*ciRHFwR~#=g4iWUFvU7)uMaP4lfJ1(@;f}xM|wLU0*>|k5lrooX?!d9@|2M9IAF6jF1C%vS8m^C03nv'
    '<^g%geSpN$c3dIOcQXkv$ZfHXmS}Q|o1jGng<?X^1v%7s3#3#<8v(7_P(d<5J=VY+9fn(>l^Dstw~T(kme_Eu7Cw63R~KthFsjhE'
    'q=ao{mJQ?6T+b3J7$@%GZEwrg><pyFlH5p%N;TKe3>PAcp!*nndZD{N`TBk|c%uP#TV2(m0jFkx6!5F%2Uexnv=1}5CpTPjq^TBa'
    't|%^ZF2-x6&h5)NKk!&wzF7(VAEGqX*Or4_NK!{Xa!Vlk@5+@S7Dzta)~*!YDag{-6k1d&*2Kmg&N(w+3z759`17`j&Ko2=C*`%C'
    'gScO29bUPpqFxI{3q?C9c8;mQ6!c-*xEx@J)+oH9U~txD23lPX_KEl2b@09N@I?C?^$C>5NEy(Fh0MS5;1c@ZltX<Dj+rD5QNmtt'
    'Aa(#Mnp#}L>{4)3G^HC@f6M1iZn6%l`0tZpy}bFon;L%{%Tfifa~63Dr`1rxM+cNnomPi~j&L}Ip+G7K+WLJ#>358jfvLlRL;l`T'
    '2Kw2Uxs6>1|GR5}{!5)*9Jc7S6{W=mSj`tMiRGG8jR)#N`|w~~5QnZAu8=gh*Lot!$kCr@AD3MtC<WQb1Ci^u^`&{4tVd)mK#6T^'
    '0?L;-?z&(qsUwd;S|@hmQ7Qw-QL?aja*6-!PkANAL(z+H@tleJgp~!(DlJG_wjU3_<Lj>oAB(tFZpCNzSP%(4n31|OhhX-%LJT_V'
    '=#7<OIdsjMheX|Y=BGY1b&8+Hw#?K&M^B3tR#P_*{=<&0Dm0NlP3=+IADpHjcc=PI)E_7<Yw2+IC{D=7VJOa1(Ne7|ZP5f1{=y_|'
    '8ZCi?YT7BRJkc#W%uNq9`8IGTBXw}fXw_w*s-stXRIpQHJC_0L@fMF%93AQeo!M~xRl1n!ZLeHG&Gv`tB_#}WhpY7&y)w8n#Qc*;'
    '`>jYVsFd(Y{WZ#o^@0~>=U1R7uWw72Q6=I0$ajebS1a*ujr<Xnblpn2Wv)NqFv5+!@#s}y_c0RWrKXnm^Z-&CP6=nQWCO>3%<ga0'
    'n%|flVj-DtAZ)5iMZ4>8pz3YQGgAwORFr23?_B8J+2l!BK|?799o;d?@{j?NNRPHB;LhYX!CFQi9PFrK6zX=%VtXctK<UOR$I4cv'
    '!zH`0E|II%Y?(?;c>43u1WW+4_~JQa!X6bzkFv9ZWH9@nKyelB%_L0Q&^T4wXjV(+6xymtchgGpX4#q5;m?;%)JDTsx|gGixDZ>E'
    'McTVn?}qyuy|*)Urk~DJhb0v&iC9o1{z$*iPm`QE)7pmre#qKG2)|X52z94eQU>Ev61^$vo!!URQ9&8l!UOACq;9R9a?*RJlH=?a'
    'vOzc68RwkJ=5{NRQ1C%X>tsjaWfXZ4pJL$}EAnHpb8A*tCb|jjdpI8hYF?8CbT09#6`A3=>quZ400C&3IfF+<YIY{9m}&>JY!%~x'
    'EZ1dM(6b_}S99}zPUl&JZT;RbSQh31w3DeIw<n|!=O9d`xV;9K;=caLxP)%9aMMYWZEjq_uKAIzf7x9q#1#AV8)GZi)W*??Aw*O~'
    'JE1lLv4CHDmsrwg7RqMj>trc8cmxyhDqiVDg~GfHFu0aR*~!DN?tIxc{0#6)lCg|N-<)34oAOS<EJIS1s_eEHz939uAtz^zY1rN*'
    '8#ApK%<LN|5(zJX7agg-zMjy~O`z748kiC4aCYs35!qFH2cX3X3f@6meN|2>@i|R7uER|yKxcjExm9O=V6<gRj~c@p=%zk|VNPZi'
    'XQ2xi6lY5=%Mrh>qu1KAsFS8u1DHm4<UoU=Ofyd7k_HE%+-;RC9$~0xn$ry9<H(-O6vx>VTV~)p%u!>q=M-Vvl2;NDVhcdXu^eHL'
    'O~wTtsBEd4<4=@$X|YX66K1|9BRjav9=3=>HkzwWBw)&WN1iJ${v2~<G&#bQl54{<_(n+@p>VX!?wy6A)RLSQATzAwP|omvqD3L?'
    'G0bu#*rk$wh%SD9m-Df6Y2@Hx`q+(2Q2@e>D1n}RK&1kJB<Ft^gJrz>ny1&!2WyL;EEAO&H#Aq58pp4x26i+w(KD9E-2v_3Pcb)Y'
    'hY2xxl~?ps8w^$@kddQq{ykS?-uk=wxg{c&V|E?c3RFhWqvNho^Yu)1@PXjfKF&M!Qac~ics!%*clJrAn)B*a7mj?24-b>~rR4Bh'
    'd)l=!$c4hKFo&rHBmBMzOsSiDa}%=nI}WYg%Hh>9e@6iX7Vrs5L*G=e1>Qg?@9TAk44hxfWxNel?=XFtq2SuZ4>A=3Q>9Ud@*Ycg'
    'S&QTDWj>+f&LR!YrtW&j<=oV!r%1>7b>BM0Im{~S{r!mf4MKO%!9XmCh}b7bY31EJqf;1C39G9mEW%zoE+k)cVE8Dff9gVVQ(kzn'
    '&3?lvk=*A7LZqAsitLm?J>}r}7<zOLH5nki%aQP{94qKjgzTWfe!Lynk3ILnRB2Y=D68b77gIJo-qJR;(c=vG*n{r?Y~O7Ro*Z=q'
    'n;xYlf|vl*3*y^%qT5)Tz$owbGs~uTvvp}4Uj-f2(j*5oe}k^fioh+Oe3_cIRYfK#4hPe6s#I8Ont#AxtlTfXWcNq&w4A3?brPS-'
    '-m3w=Tj?cbAWz4N-6f-yi^TPtP4R)U#^iUZh4ff+Co`$)<p#Nih5(5a(C^_WG%5GG6-&7RAx?S9FwIYdDx-!IuFu_J<*B;vj3Yk`'
    '=<FNlenQT*rlH&Y)aRSi%k;!#-oHwd8eB03v!h|zw@JDePptnHUoE_-`qJft6*ucVZ+L==dZmFb%Q+%H!QOv^l=}%t{;3YYd0K26'
    'ey;ML8l0{-%I7)UBZbtu2O`I1)O`*$5Kh0)bN{<qgWxy-wuxWq!f%W<?`qXLHl@&dQm<rFo1ZEj5zRATgBSoAWHc^S_?*aDDhI-o'
    'YC)o2sIealxhaq!z#LQ%0*-{lSHuwnM+51y>!HeOi6XMdF=+gn=SCL8$zC+w*XgolY-L41g^DvK`;pMzb^?BrXsyvtxM2T_N5+fy'
    '!S7bBE$agP`9@@fMVr_nPmNbE;bL>P1aGXCjgB_u&>2+zKEm&<XeSz}k8{&1xIT7>P44S`GzTJ|XEbs4Zym~R)J27C62X<W(rU#{'
    'ieH^+ph<};R8x02BWSpqs9A5O9uK{LQU!z8l45oLLN6q@ZyVdp`RyF7D)Qwn?1m$+yVv9(maDr_z!QwsTft=$bfvR(PS6N*7TIYw'
    'CE17%Vtyt{QnCodp_h@(h+=|r(f;DlakeNZpuWH~ym&#o_ytVb<8o_3q;zg?FGvjH@BHcc>8obThk5@7R(yL8K!vYQYD+-ZEj%*x'
    '&`J7ZFV7jOXQ0^#Mf}VSA@_5~-49K6tWjYh(Pii;J>Thxtyjm~zeu<3O!|L(WNeQgGmH3C2kiZr=um1$(!t^^1q;91Nm-)8+U8X-'
    '4J6>)@9^P$*)w^o@k~Cmy#*k0SJLIkRYh6?sF~cZn%uN)cu)5&`h6L8__<t)2xV-bJj(DRH*a9kh9>2)aeBRyEGnhraCzQ#Z{cL8'
    'e`GL_4Iz}w1k&W#;ETJf^>CrJ*xbcJ;g|29zkK@hZ%>iVHW`9!Kq#EfQX_);ydcCOn5k+k4nl2uc2s<Bkb-gKw44fHzoK$mXr##('
    '!-&YFC%)3GUtz#w@cdB}JK3@qHezKHyrCoQpY_KppY%qy?P~gEs;gzC6uJ+hIY?bRooI30cIGa52;wNL3bn$sxyCLcg1?eHILvbo'
    'YuXE0cn&ISd#pV1^TiL#OChoJa=Fs+;u~@|MV+GU(d0fR4h{O7!}N<?y@4)Tz2r7wO<9w~Qk+s37=luy;?(2f&4vuk*v%XV*sVZa'
    'oL`DPBOoZH#BJJ$>G*_$$l?^tcP|<TYi`0wdox$sGqThXkeDDnNv}JKwS@y~u~UDdG1$rM;bZU$Vl)RRGh{0*Prioag}$~oRS-xe'
    'OW=wiu0?ZHIOIM+=P1=So32Fy@-5l6!HK{gVcnp8e1~;%o&V8B&@P*<Heo9OTz~9vX&gF7h2B0|JfmwuFl_1<$!S}#yL##euathd'
    'YPrL<l28DnSDkyl+BMm@xIaq|e*hN9<KwpclmM5{LFpUN*_OO2cK7frQ<wiN=^I-~Ki~Rk0S`8L++L>AUa8tcSJeo(umX&`nGr9k'
    't3-&-TOgev3P(4kOQ6L3_Ha5!Qs2w*-xifw2ibaW(2mbRtAqv1P1EhcFpKOwCq-j59$ifodixFsJL^fNdUaNYn@NgnKfm1|I+am`'
    'gqQ+L0|EE-NZZ!FmlC~isW}>4cv{$wZ0#v`UosXF4xMZ`IUA<Z${U-Zkg#npE%x=IeJCCmh?ri{6tp#7#sXMCA2c>JQly*)@Kpza'
    'i%*4yElA;}*n(4f<t3{FVqmm#*A}bksYb|X=sG3bm${rE76}j4A!^X(B(FkCo>(mtyULdLE{`XrTG)$#kom#wNGgB%0pWFGQUav+'
    'nR=VT@Dm)YKH`vi7+d!>;0eu2X}A1O)M58+>oA8#JgU!$_9n>=W<_&}!~EwE&EKAW`}pmNxTP~S=Ho*Ku=LyR%hT_A&}zAJ(y`V8'
    'ifV7oU~+g_gtCFSDLr&mj(M_9dXhX>Ws}1-SzVLWUyHC~`)j7UW~ytZnkiFdfd=R}6K2ZkWy!Luv7TPYr?fhG(Q8V(rnEBlPii?;'
    'hy%@>qf!k0YbLv9vTG*$Yrs9?#m|THT>bJ6Hnfj3SneZpVsHk@l+0BM_a%28ydHO}Givipm~oZtD)|!9xz47#+z-8(OxLjHyYR_g'
    'ua&?2`<MT3c+JG$;#nz)6R+Twd6SoaCV5kMD<AF-qYr)=c{8`n&p%(q$KOBy_VI9$KkXOdY|j1CAOE}CeZ?3zxz5Db&wu;-_pirK'
    'SnEm<o!VTyS;klI@X!4FONn$C9B=ZM@1MVX`t!$M{`Os9Gk^5{UP&{C-`}~L>=cnFT4Q`b<|e)u@2!vDNL)s<hmMZn6`jg`uhLSc'
    'g#G8v^v6F1elMIJNA{(YtJw2FeyoV!znywk<-a`f-42y%W#8?F><{KP!GSktaC}v89aD~OtnCg7ok^4qz97ySlz~D}`S4HA=BC&c'
    'QoD1LT#~<yQ8E3Zy#MOyUO!vs1Xg6obowKlXt$Irq_b-M$59?t*e@abmVAbtjHRp2NV#t%%SgBWj3nPZP(Q`XH@l+5g>Dw|#1&WV'
    '^L>ZZO!Jz#;3_vaSr+H1>ROoTDW~EYO)F^6@0vsY@aOx(k0tvG9dbzUo%F~d3p%9h%OSa!>w87>1ALUT&3HEHWKxuLF;r6BeN(~6'
    '4CfvGPut8Qg5T?)xmoyBsV;x)c4PDr$wQqr+Y3KpQ1t0%u6_>uNDj%Ad5oW1VC(BgP!ehZa&M#;my&d1^^k~ze-zwF&d&!HG90IF'
    'eZx&pu>L~48FGfN2t?f*OD^p0N0p?~`x^{^f%0~?ph!t8zrm0Q9s?%pUSz7vSqc^5Tl)xaq!V?rX3KAHx$CI#=DU8X>!-T*@~isq'
    '|NRel8aidVF=OX9E-naCO=1W8O0vbKn#l$nzM%QY4z7U)w&ArZTKP%-p5fsY`;ai5D3xQ|Cli+Vr1<h>8KAx2U2g2WmN@Vi6f`Aa'
    'jTxZl4BHU~eQep;K;Rw7ec)7KPC=bwtH6!^Jd^faZ5dx>sVhp_t3Wx6aUiQHXnuz62z8>$2a&pDA8wW1g)mGJ$*mX~N=}bBYDK<~'
    '*YO;5du>V5wg*ZtSL6ug)1#_5hZ~S4Lkiah848N=lCU(p4xwfqRoymcjaa8pO8vGLml?&S433m|6MjGkx2K>~^Y>kPbbe!REXlU3'
    'w^#J_(S?Z)JzP1v?Wx>E22pUOWj*xP+9*u&4Q$FQqy5{+Casj!FKTm>X{B%~GlKa^wS~h<mr%S8OMaJh&y=#U!OOIHse5mQHMtI_'
    'jRozvH!vMzBei7D>wyWd)D)6da)Y-76WDzt$=exTBYuP$99-Ti2A9(V5?IV-^^$NRhjOgQG8encOqZIjDQW=Qd{(3!76;#u)(A}T'
    '(#kU8S=V36#KGiO*<dt+4zMjRd!|{q)Dg@xL%(11483G?R%!ySmG9}8PhMxWEvK-tYTm?C@-Tl>8AU1**nJ9{k{Mkk-%ASC=+5{='
    'A3jH8^3ASL+Eu@?s=4<U%P{FFm1J1@7C;^OkyJ{OuFn{Y9R~19q*hHnA=)jLW_bzJhG!C#IRb4Z%Y*CP8`ziP$#g^~Td`Y}v~W_z'
    'W@i6D9Y$x-PZmlIpzl*d<g?3c;}35Qre>N*#>f&%2$0V{OO_J8&QH%zUt3R!LfEJKHPKK@v=}D$CYbTV2&=%(<Is}#lgp529WKsH'
    'OR7ZUm%eU7;N<YZHyYEm*y%ktcxyK-%bndq&rZc|=A^h%w)<>ava$Ommt|L&g3#}=vN<YD7cAka>3lhMG$a>9BXz0P`1A#9;N_pD'
    'hwH><Cptx(Zt4H=?fK*Wm)-O8Kd_o4iG<R<x#@xpWydI#ReM;z=Cul5M7;;!lM0JiCrv6y(zAEbKps1YKa#+O&gAf>Q>$L_S@uT#'
    '65HwhVluuJs{0w-JG#%b#JV%>srsWefbZ1$a?@YCG=GLv-)U%+)*@OGi_=+O_gCbfc=k1)G;flvp7)9;nZ3c^3XM+gHTP6<L=(lv'
    '!Bzv$S#KML3V9VBF6z>a?30t<#C~7MH_5Iga)?EK6?6>c`z)zLUfo#X-6Z3W(&G3KA-I2fdbwlXykERujZqEQAV-D3Nm7ggee?Ru'
    'z4&%4ylfm7xe5K)kE3K@t2(DJ_s9S4c3%^J_2eUT!Q2HGN33B_UKJ}Vg!kn<8B~VNG4$|Xfv%}f(P1r#v3P5dl+B^_R)4P=7jR*o'
    '7wmhrNQOgHR|(P)+Y#A9a*)V8zzQ*qW|acUvj89U%lFS;KK=RQ+kN|<7zqbo?a4oaT~3A+=S^%q6DmuLxVgmPsWO<;7k>W1<133-'
    '5S$V#YLnY)bWV`<F*ckeOXkri3pFg3NB$@tq$CJ4kfy;Bc~cFJA|#B44p<9g2koHY`fTK3tA@r#j?Tz}hP*FliIe&$EOa~Xsx^S{'
    'b~)qK$=#jV3vOGqOHyG+j%=5vbu^S+=x8-}0i}f*IvRUY*izA(DpT<)0XY`obxR0D_PpMs4X&iZIZT*ica{cEx2J_iD?PCOHUJuY'
    '!-gas;-^iMg=ol{^l0!?ZJ5!+4WLbV4yGwaBt}ThVJWp7Ts$a7p-`JjB-GpHKnVL??1WZMyC_lEdMpi&INGkfO)~H~J^yr+Z{xo='
    '1%}+OWQNYI(Z4yFcN6*|V@<Z$pClE}j7~~rCIi9um1wxd{(kT(p~}+CWSKBHVg!+py0OH+sbQCt(N0&uNzh?t<v`xtNMk}s*K%C<'
    'PlV%(31R3*s<F$NG+=Hu$3Ga#RdbpQew=(f1ru2bP*7?xxgukzJXV>n*9_FGqOO+-<2e#dIr5B>&)+9%V7P-3=YtM+<i#zF-OBx1'
    'd&g*WLQAI6!DZ9VhPZY9ZjcYyezI1WZhFDm9R7p^^5jnhQa={7Y*@=y?Jx<c0g2A)LZ7M#(B)g9%!}4}IH_u`YP((!zrTS;N*K3('
    '6`?3wH6dT)WYfS}boS*4(<a{Tazri6(NlVxk78IW!AdqaanF)I=lW`P^JIhTT;Vsl)FWS=5`8m;@cRM0=rV`&DaH9VD-0;5bh!g1'
    'OP&P6tQj9m?g)hQ+vhKTfARmf8nh?c?vje?#e1s<Z|=YEuCV7BO;AVodNY6$%s52|sUW0?GbUF0-~Vu@As!6OdQm2_Vc4k@s!%FE'
    '-Ik+4P<gqt0k^E=={rQ178X7t6T0`JZ}JU&V{7s#lMBpGp!>#Ei_7}D*8_wxl&zN!L5I$Q1yEP1a(UYav+pmVVi62?5m3+$E*~;i'
    'ku)C|lg&fn?^*}YejA0AWuK61Jy^j0l|VzFI6^syhMu?wHN5Ml_C1nigcRyHrZZbq@1_<CPu+fBjC!gxBAc=(?m#GT<4{ChRgnXi'
    'r=*%R`>A)Vs_o7-7zRoebbLR30F{_5^byiUGdues297ZXuV*7#IM+E5dYJb(fU>Cw?IBIT3`ms^=!(+P(XXikDj!HGc7sGFT-UI5'
    'B@NN$RH2FhsQb23>pCG!y#tpis#r6<pXt&K!1#n-K_pv><cqL{QnQ?O=LJciImhs0ZU3Z%D|QhTd`pm)qUHNm2Eup?ZWZ%6U(}MW'
    'M!PV}2xVwHAI7LOae=8}K4h7NXqPw^q4k3z6oDF{daP=8Z9uFC+t=kGk_7{5$bttRSa*$j#X8CO`j2j-2_AWz-Gw%rf;^I|gG!7Y'
    '9DHPy2$2Mj^%UV2LR{DZ0a^#K=jP*OlSm8!%-E_kmeAe`4cE3#^RY~LaQkzaV6hoRX;#I~M$1r@ZJF7bZ#9uddlNv14;90{Ub4;M'
    'xU<|DZdHI-$Hy^j?KT?pyt{kw_?6i)Xd8E}p+ML5p6WdaJ5A(z&4WK;HydodXX&R#z%yEn1#<xUHVtGzl{Y{^5=d2n4n~SYYEOz{'
    '?QS-X=HmwBaG~kjWcAywKEu-$TmO|==2?zTR${3kUtN)n)O6_izORE8fgb8Sf*peLst5Y|Rue#IPea$zt)HsY87`01<T*<QkY>at'
    '0}Ibksk^eKsHx{%!~^x7I-Zw1Y#qKZUBuk?jF`8<v2dO*-ke9wl_7zhFQ&fA(&8H|0E7gGrD(7-`^ZB%RKy@?)>dh40v1t8(K`-p'
    '9I1zr=DRyTfS^w#8>A;B-S{jGtZ_70E^`1z7iUxDaCRgi<$BDHPHtx{A}PWsH&-#@JHk(90$I_2mj04#Z#|6ix8@-wlE^ebwm4rp'
    'XfQuZej@A5-Iu4|N4z)Dz_EO2^xjAhk90O9%sLO^A}Zigkl=D13_~m!@DoBD_bK<;M3AJCuR5Sx#US*e*@$5;D~+Yt3G)_PTZ3g{'
    'By?Hl<jbwfk_l(FivtA{D$icK4p4|U*%TzUBl!X<I$;f%WrxN73xjFkaiAMTo0_qx_o<W=?g4d)JI};s2YO6A4m{4lViE#FQNi8r'
    '6}?i@`<L&ZzkK@h>yK*nJIDE`5ymW*oHrg!E9&;`>?zwZ@-|ouTjaBL!`wVki}>@GzrXnZ|EW9Zpve=JI;-EMABwD7i?mNpq`=p)'
    ')2V7r&Fh!$<ZAbe;D=p!+y0S$EcjDP#78L1JJ>oTdGdF=FxpUWR~aW)q4AfBB8UD4IWf=2RlU$U5Ofl<Yq@e*EM<6bA7r6K{>5ao'
    'uu@w+!zq&&zBC9dmEX&Ep<wb1QQZ_3PnPGLRrYF9Im`b5$%+jYcA4Mu#gM~JjJ@n%_3+=Gp1u|nV^iJK@n1$_<pQO$e3lkB4v0~t'
    'LYBuj$)EbMc%PrXEi`so<iEDL{FGO+@A5PcQ46i6X(Gby+*kc`as4PIK9R)Yn|v!(V0yx%02FjuRG=umeu51T_5>*wQGKyd^e`&y'
    '>@F8O?U6kTR^4|;21%nKavyO?Z~&4&>Mr?Q20c?h%%H1M^ra#GVwzWKh-dc#65av3H_J6RRlD=ifWIDtXL-dmNF+HD8_d~kp9|k('
    'ttm7YjAUU~vv0@lrLT<-E(@v-5wf&%s86#Sq(uQmwn4VeP2Fm^oobd^lQ_`<pHrPwsTkrZY)d589HYb<HNd(<>Z`B$da~ZQmuAsY'
    'cj#f39XHjwkA|9SzJ_ZHTah<!z^H>TtGOr^CknQ_5*!ktUCyIPt825OniUS$l8JpJb9*RRXBlc9Iil1*?vR`ga~mI6Z>dd$$qLM2'
    '^Oo$#b=us@>ZHDAeQY<WI3pTQcH|2QGf#wS7IEdUk)s}3eeowf@$STmxT*Iihl!rUG+dyXbzC+-`umk=V+f_au#-Kz*?66P@@eYC'
    '37$#QLmNpPLs{A-V<DK_9D7X?Bb*e$E_haxamn&KBWj3>wj@a7%7d$nfuak6decz!$38trxSj2T;*hCwR6pGlgv==W@!@Jsx(4PW'
    'E$5)}6>CEn<DK-v$EByIFH1%7!+fm|1A+IlS{#wvI(on@SoVbiZc_?WL6LX^W@L)k93dK{G?1u_a!RlEkVSDzovs~rL{cXO1!rYQ'
    'PU~z@Oe?y9?hTnro|Ng!^I{S!W#K;1Em!5NhDbIhN(;z;`b2eN@|71CHo~!zPPweF3%26BrV0!e3_=zN7EbJ*?%iKEb@9|t%AK`3'
    '#kbu~X~+Wody=nMhQ$`*U&CU_T?I6q0gx)2VBRXY)}{P<b}HtpjtszJA)*(pfzr9XOR<CsYB%w3iOmGj4_t-RtfQY>xOONvLA?zR'
    '^XCHXtDEZ44cTjC!Q5nSq3seR2!H=xEo@zV`uyuWO7Vh~E|7t3R}G-BuIg{xkIvfd?9F2N9YRSp!jmP7KegFgz95ON??C_&49XiA'
    'PgyF7ax}cQ4L{c@AC<G#L6%A19@_#(kucpVgINIm4I8vMu2KCvLP7lg8=DEmAFn4bBO;@WfX6F}zc<#u*2_iYUsRz*)5LjcnV$Q6'
    '@koMjSW0~PRZ3cct{Jg07*dgw0CX_b7r=mrjoMwu-j75(h<4D!Y~SA^VZSyr8mH_}juc^-|6Arh!9R+=4$0#7b6?PLLU`bBKsFc+'
    '^3sKx-J2pdC{SZ~!(k;Xdk(_K2s3j4FqK{G9>4_WX0LSOatIL{B(2exp;+s@VI?c-g}!HpTzR27^<3xreCmwvyQqBvdG07|g!rNY'
    't)^@B;pzP3D2^%+>UY(kHJ0>_wie}-KDOrA!PpluAkDz&^J8R4Ede}f)MD7|ltA(=qiQ`m<ElQTgvHc$Wx@`9s)qZXRYSexB;1%r'
    'A-t(f*1bMp3&SQ_5(dXhMV3H4BTOX+dmJ>>yeN#qC^(dYtvQ^<{qA)_N{5eOdqM&Dt{Metfqmp$Fe(@m=$%QD#!Kmt@K?4}{F8ev'
    '@Ps;!eEW|3spU>rM;wxqf8?&x4&qAw`0JG-BC3%vX?Ms2zyd)W6d15Xlcl{uvUhH4;Ucsdi=ypP#v^9r<x#LL3tB?YUCx47=s^y9'
    'Uy#P<v^F3R>~)r!C3S8RU!KV|RAnH;qt2ql;1xUl&)YFK^$d<`eKD{KnX{AvhExdrq94kAZ4pxM)WPgw3ZX1=vaBRM)%zGY#2nGd'
    'GG`xEvCEY0{8QE;cA*F3-ejmhJZj0To+REqYe<2p_bO5&RxB|ffhoSlYQO_tG}2lo*za{H5}}>pfMs#RRM24GXY*<kVwM~j*@qzM'
    'pe>OV0nLX)F^h^}m~#6^Geau#i}f=s%JL;T>^JX+s0)?V2AfPKoot|R>_(E$du7p7(Zzwszxe)yyMCO=CDouE3yIEvzi?EfR@Hc&'
    'L@&uZBRdtQdNf(sI47fq#!pqPpmz3AS`CX$MBcUek;PkEoyn=CS&b4T*hWsqGpD`nNn?6WTd$Q04S+4kxEZOWFSPS`KF!U|l?2m_'
    'P!ptG-S@U-iEcp9O~p%a17K|_>Q}6d_AdP+H%*pEt{*NB+%r4EZ9}*X-0{*n6tp)BKxZgHR7}Tg4oB5|;R5%I$W|5_$<ZVkK+WEn'
    'PsUv~TZs{O<%rKNBPg6p(i>r9VQglK_z{aXDWWMXM|QAOED?+zJ4!>5_Xo0sq7Y8S?1ku@)1utvDJA>MkEgflawT9xy~)Owns?A='
    'Dp9A#Tn-2Xx3|mP|4*NPHPae=XkpfWxI>xM#B@uyIO7Ru@N`-~T36}@mlRX=){km<lAHWQa?9&0AQoKVX#SUFoBAe$aCcd-73zv8'
    'xD$<PzjK7F_D&&mhL(E4%3VfLN8|JxGw*8QPbmK!XkXvrP^T-j1212~*7#7r6B?k~BwND~#oe8dP!dobQrh99<`A%|m)cV_E(^B6'
    'ISC_h?H&HPn011)7tnx(>K6%XBz`wQeC<vtq=6lMt>2q8y~ir%iNwOuQ!E-*mYJ*1WGAB287F7Fpe%LhA_^5a*#;t;^4KGQgdv@Z'
    'l(tm8RHJYfMxl`<4H6HxI@}x2JAAlO1)I?hh1d`_TN}pl#bm}Dw@i_q9un#4=tpkWAK@3iSTpOn`{E-)t?iBSI4m?UdY>Wa9>2tT'
    'BP2A_#*({VfsmwfqSy+B1pUDw&l4FQ!7egr>zhlG?tFtRAzc4#bFXNWWXd2Grc5>&SvpGs$xyHcf}P=JBQ|(uKO|qvfTLLeTlIM('
    'WpjiaOBXC+bn<~~vvEPfB?nz%Hxyw>!;W5>DKqR{M#O)7d;YlpW%vC2k8>Tfy3)qPy)&7ynFxt{9s)DiGrBK_YdY|~VSkWAp6{6z'
    'dRIGpM_FLG?vyUuISz6LCZC-~kBWbTCrAZgI5(!TLx5TT^jT`lM!G+a$_vJDlT!sbw6{!f%P4aeQR&q}QsuUU^<67@m&H+Xb%MU*'
    'EMaqz<lha+^vxIN$7$-eI!(>1mE&MR`@IMyn#sy!rS-(JOulLgw=8>*0l^=1Wlr}IZZ@JG0IEmg5HuuPO!7)n;CXwd?Q~OKhQs}Z'
    'zVkJq%UnYn!yJ~0R`r>bajwH^NvY7rz>!<VqT7mm!*H-i!jFDYHTLFC+t0jdJX~=|bfH8+ixFe)tqC~?x+;oi3_f02e$5zzxqddp'
    'P$Ekdv<0+)ymwa$by@u86@)_48EHH7I+($SvP4R+euesQ$wDC`gZ#LqFo(7eR7QTMAL!hSD1Iuv3=Qm0nzvC;^2=evdJ3y&PnyCR'
    '7)r*F5;DyV!ESNbmb`9fg<7QD{NlWV&|}54v)PYS2H-J#;S2RBKF2WD2V;ii3or}2iaCt~uQ;8If)2cfzJ7}jQM)m!2vnn`39`_d'
    'G<hpw(zswVss$p(ttu^|%7l>aXfyY=yz+;84Z@PzvCDQq+FO&Q!|;PWI~gq7(2mNk3AL~T(h6R*^r5YrCPaa7^KD~r4!L2q(1>yr'
    '?_S=QR?w<(MS-&W(Vdd)x^(X_?aN8cylXB=rk>KVw$71nZ?FJCa~LWXLbe_yJiT0Cn5<sVqKC{_RYh;|bt;P95u89$a4HMeKf@f`'
    '7SH?Z;Z|ra*0j0@*?-&eC^YD}qiIh&lrIp!uPUj7eC78O7z<i1GbknJUYd}b{C)}(?HEmpte1ksEHa_l<(3bg+31ekz(23zZ^q26'
    'bqgl;_v2w<u~;|)*&l)C?yt<hEAww@27;&?EiL=-=E$y`Ybel9JO}eeYy~sulb?x(z9VLV6D;1B#W&oCLA$Ntli@|^*j;f0`z=u#'
    'UzXUeK_xlq!MrLBvP_PU;?LD5$d4nup!2o<TcxVKiCiZcoXKUvSr|<wZXMdm7R5_kjHd}zk@oIEGZd+3;t=lTrRc?VJN=p22ESbf'
    'c>$b=ev|15tgmcG6(L~tdEq&!;;=h`x_9qFT8G(jR79ptJpFs!CK!9WT|LjWhq>W4pB}jgZe1h$wz>@qH_liNNNTDo*BFMqa3(NA'
    '7uI(4+axh!^t~A*FnB3^qac&1UW6r($Rke_G^F-NGbKBT%uWt5$3B=;p~PbHj@x33JHe8%(|vVy2TM|rV|I4IIC>&t)zCIAmZ;!P'
    'a*KgWJD3DUhF^ioS}rTTfo>jYL*+<amQ9;i$7rE}Z#ScY_ZPkdYk<}8O*kE_a=y8%xBNmkT9mUPITxmyV6mFTA;Z(9Pnrhh2An*H'
    'VlCbJXzEg0b`*#QAooepvjNE~Y<zy@ZQ~VTTc>J_Mn~|}T+g9oCv@ZkNOo;Mw>20qG6Ja~#_DhEfF-Lyk33xYuh*;E^Iy-5T_+{M'
    '8az3vTW?{Gd2{(bBfilyFOrsqmrcAnFN4quG%k4tM1DZ~Fm-g2tX0E}kz$y>pb{7&`Xh^!*K$NwFJa9>T?~T>N_fa*m)v6KxGdjo'
    '0{UPsKwuiX{j)2a4axG#N$|?D+fhh_1v)ODu93x38ff4%9pJYavPN}GNULg`fyfqs&ZK(~>mRDCC)vwd`14G#{lGL!2kpmIlK3$B'
    'g41~}1<6r5I%2v5t6(rnsZxl~8@|UGHT4*2njF!q2vStc`L6YCV#p(C7^Mn%hi6X%%X9klQb8@jH{%u-n5f4}Osw5fucL<<X$hb!'
    '^FCB(H`gA`(+Sv9VXTHAPZI)#15{r~xp~4GFO7}NQ}v&+rKi{>AIt5492U9_Oww`PL75RMUz;6+!0yY#4!7o|KPbEzqa^^$V(eol'
    'Y%t(8hz#?pdm!qok?u}C<D0BX<;sO5aLbu0Vm6u&8lDf^d;&8LEbcD@S_KixxQE>tKH><<_hpBNrjvyUv6xv*p?i2!c3kc@b+I`z'
    'iF|pJaBQYrDBsnrhHdG6#XIdf5@d-J`n&u<N~m*pB|}bkRV`b#5!Abu1-XFWwJkmIwqQbnGxAK1MDFLfC%37&l}^baH7E(24ACOB'
    'V0Xfy$%amY+a`-HSeSurMV#o-?jgR)43?M4akyeI^Vl>@_vIsJ&!9y(&qQPKU=2^;Ac!XlA@I*Ilk+2I!%n6gJReapS+1R!(f)Mk'
    '$imehEf@@QG0~mqrz=2$+unNBJYkrF$Lx-!nGDcv>a{Nvd`c~fn#aAP5<~1|!V#R<G|i{qZ(8>7@uIoVz7)#c-_G7GETjeIRj@zc'
    '#h0wR)ZrvKrdsTTdix724>rCgM`wpoyjaVZ&9(gYy%16B^BAF_!ufAP=Pkz;NT#D)`Ps#djTaGN%`nQ5-{_eX9goOMsMMf{Ug&7U'
    '8x0@BX;kTw>kAo_X~-UWcAgH`-b^jz9pq;`xEa`Fj^YPCQsx$*(f7yT>6O%Aj9RC?FCX2ZwG`Wu=Lgn-*Ipzjhh}qF19I1<-(XO|'
    'iN>b9hR>x$%TP=wscMnt1%Zc72V7-EPZubtU?g}{)bSnJh1#bkTTtxW`CFiwFBc<M!bq2{-jQ`R+8sv;8o?F{S-YmgVF!wAo2&G7'
    'U6HwHd@)=mlwG;G@~djNAhm{wA_`fBW8xbm)OHGPC5B_ymA#4nO%#!zdb2)+MeNz9l58uW<Moe)af}4nK*%+*TS;9C?f7`ct)3Mj'
    ')vzV{%6)(q7VLT>TTJ@1vyhqvvl&`ZUg~n`bZz<2vz&!@1oZR4%&U5|#v)I%7DX*Ol_CdW0=j~|c&V}+D=T~(l$SgrFFzczsL&}k'
    'Gen5&_*d#tGYtrQ286T$7>fgu^M%(?n58N&`Y>*>G{+C7<?O%;52z9S=2RJnB9+wo7Zyvq4qcd%6XnfN@Qv4ms9c%w<1Ry*2Ej)U'
    '#lipS^RJ#`snL8P+lTeA9~^ZeI$FZKVkO7j^cH<v4U({c?(3y{*|wYV^wiCjF?FcGlUjWbZ|`s5p>+Q)tzA+EMEmy1Rj%Hy#0<DD'
    'on1Pw<UfnaoSGd*#p?8A02+-K<IVCYdt*CuOEs#gq^-NdE9P}n3P~2*>axhBmBn?+Jq26v$3oexY>b(yjVyab{WoyShHw<^E_D%I'
    'jo1}N<#TL{(rF`1pG$WWHnKFa2$kH^nRs_su3VF=7T2#S33N8Mwsfi#_S_mV=6(uqdPe{Z=3~^cRW(IEH6UTpP6m1Z0>`>@H1W)G'
    'xU9c0`cse903L^JLA_bc1u}IhF%dX<bvcwe0H0Dk)w--1J6SY&@SAWumKC|OkPa0wk?T+RjjV8%vV%v4^7Q*Sm{<lWD2$lB%u!lN'
    'TH!iG30r1ZJfC^Gm@qFk6~*vW8g6rE?HHp>4mJ&dyl>hmU0?Y^wgOnAWyOA_End*gzcUQPfmD#FQ2XnbdNYtd7)ojLN5Vro+Nkc}'
    'G0fZXZWjXV)&A^FXtMh%nq5GISNmJXgSZjqUk;<(0)SMpFb(6x<V$Ol(0?{3ZiZAgxKon6XM^!7IS1@h#Cp^d>@pqo2xmOC&0HJW'
    'm0x>1A!f%UjH6CU4T0QFKr(_yvbe2#y03YLey;rcpp7ZzhsXRMKuc~#94YG+rI&2U&f{V1<vQ10ij=;y`92$hP~kmFHGJ(%*HaZL'
    '*Be?uOuxlKL1zBgnUN>-TvO0An%Dv+%`!<}z}7s%Nn8Qf>F{@%33g>I4qR1(pP@*9Xqj(k5H8+Q-iXs<>|kYx1uBfmnCf`v@q^&t'
    '?r>Kfn&^4CK23F=1L9J4#)>)@TS9|~`p;=_Y$NA~eaJBmTt;ZrV)5m%!^bpQnhmUC<&y^;Yr;aV^a&seHmow6t^#;53!bA<&7ssv'
    'Zn0GoiIvW^@?1rdFxXDG+Be6^ze$zNC<vC+#f0mlX*g(tBbs28m#W1b7PGYlm&G?yO>Xqn=pGyZ?R9|RvmF{ja}(S%YgmpxL&+Vx'
    'u5?KwG+Qpb#BNb&e~!jt3JaorBdY1Px?OD$w1}16O4_g-VF$~W*4W-14H8Fu?_PXlPhH+87%Uh%X;Xv2C>^}_*KZxJ&E?z!^s_Wp'
    'Qp0W8)c{BT@tJ)64q1{alSE(hkuFxzWvMKL98+oMo};TuOaviQ&&l*>71X5CGK79_C~yc)Z)$R5ZY!Lu5<w5%;SWsq{9w)Kn6hW8'
    'MWx^dZBiC4M<?--w$Mv{3EzUWxN~`wes#JQPEWE-babUs>E1oeY-`SNJjy>quDqA%wpVAn>8@J72^|p<Pr@I!8s(8%-VF8ED7Uf;'
    'PD-6$L7n>L`z8zJ$W8!W3g|e$-lwPQL-K(taGT2=TTxg5N=}Mi6*lM~wIaog8C@#eayq~x#7?EdgK#E9HYn`pQYHHjqT*$DOAFa3'
    '^9{<zZ#7+EAXxiaE!WHUba0#-B;SO0=eOq3xR+u_(JhFq*BtgV_`rOpP-e~Ub+z0RI0798kLcg@@vY|BpXBhos>*B0VN-`_S1auK'
    'wl~yP4W62#*gSeiI>G-sN)L~+cQMCduim+W1Pb=R+f=C8uW$boHl)y_pJ02dhdpPT3u=LB&qk98y_kmwN=|gQF9q4@7-ey1862uN'
    'j_LIAEsdt+Ny&(3MKgR8D-?c%L-${Wc1D`3JTi(-(RAzvZs-A_trkLlDGGX6M^VRE%WmA`9yQJfh94+dly3b8ao?s7t>Exi9=aZf'
    '9qcEU!xyLIYxMULA9&#sFY;rcO{M(2B3CU~l+@&oMPlhpcz&su@gl<>txEeC*y@Uh+L2^q!7ugx>1=d>oGuj8Y4O7r9tCn#0Ur<2'
    ';5;|GC!QF#Rk6n?ME`FR=ea~{<TQcu$IE_x`nFI6HvChUAMI+zr&27Ucz9?l$HtG;v9dOAHhN!01|7aiY3Md?ZWEXmIu}l;o4@HA'
    '!R*-yY?dkA{7NKAduuW04w^zN3>so6$<b{XcR?PZWv*Ntk69`D&YY`WY)UDgtP%`#B#8L$Go6*1XhO|*cG^uY&Gvm%5)n+&MNpVP'
    '6P;D#@YfAbCV^GxIhDMzw6L`^Fksr#;dt)#cIK%<NVr}o+Ufl+@?LvZ!qRMo7BlRTt=LZ|y2^MBrzxGh$f5^^Ri$}<(GYNeue&%;'
    '47|1}DkHWW7WT(x^a(6*!h(yX97MH5Ssty<MFq8xHRBO4a5yoOJpu3(B4L!?8(PL_lMBrR=rGQqIOMg?*7kWqFM#Ah2&ZVU=ZWq{'
    '6{1r|N$7(i3B?ay4CXspC(%xGT5@@faA=A0*-be@L?0z_J})5sv^O}C!@uTY&L`e>0G=`;7IGL8rv<z}Si7Wc2Q(;!1C~&cOnY;M'
    'A1k`XHi!(pD{}a~U+W=2Ii#?-wU4yL{c|0On87&*9?*B<1NT$g@=>E$6Vi238MqbtG{mx5#(H~=j>0DBlEqpP-rJ4Cqhn{i!w$@S'
    'EtL^uAwF_Hb@{HYHjdT-6b!>}!9DCt$I9Cvu89*_!__5;hbVE<;m1N&x6$cqOP+A2*n{U)<?JvNGK|I^FB>h0te1I!&T4jGml6!t'
    'HtY^EJ95x?xnSugFd9r^Gp|k*$Xt)TXBIlYQ1NJUsHi!p0TzXNy}d?m9&Z^<$G*Cl%+;&k_tr}y-jBRjRRoh%3?w99x#So*JBB9m'
    '=~X!$iHVuA5(tI+8@f#nGX8#Nq<$!MkLewrYyiQgXdReEkQrv8Kq+wIQnD9|vDzL#KBMvvu>I)wT?d`du_;M+xc*Q;6w~eTDYO6%'
    'twl;|Q?hUY&>0nN2}FKr5U1)p7MnU>RW%B!CJZaqId#Q=a-<7N+cAdUH_?2^)jJx4W!g4xK(qRhxRu+cz5{HLj)I<+^ph{rCT}(~'
    'z^5dHT1L73rhG<YIDL^rK>1ch79-9EnX=F{HB5CgI|uXiZIqVsDom$njvl31FpblU`3!Xaj^Ok^)~i&+=u*mb-|25U>ejN}OVV$b'
    'B-9y90z2~ya}7o*Z;&7hzCkM81mvaEdFecPrWjZ>a3cf%log|2N<`wHXMuO_C=d97XmDke9Cp9{8hD}S{`Vof`0Ml2r|*CJR_JDz'
    '5yCk45k~O%nFDmJ)nRi0ZPOX4z4NsD!)lo#25&kt$Y^Mi@Hvf86R9>5Dk&HHv5@*L3C7JCku6Rdr$szM6m4+?!O=j96?!;BT4=8<'
    'a&F2aXK!x&TMT7-@s(bu%a*Yvwq=!WfNV=Ow6~oY$se`QZ_A%>!TuMIj2G{N->n?r=n)=Yu({zNcZiU*M<%?NnzI(Ac6#O+ZOWlj'
    'n*4o)-&@g6G^8$+nhnAAu|tq*UvE@25c#_nAj!UEw*&s~=<6tT!c{gMVXaO_MJ+XqF-dZSYU&PW1WDtWbwkV4<DlE7OH_k}ZG~P)'
    'Zr?Vxne*GZLla6b2`{g^i;R3q_N!dojlzpy@b3yPo1iP5t#g8|N_MC@3$e8PQ3-5sulwkZuAt>IvKb*TFFa~#*Y7V5O-l<4nlzbn'
    'f_Yznl061(7DP(t_O^u7mio@0o}a#IwtSedZeYsV41SEj&fJz@;Drh_LQ!+5_ARh;E-x8q_RqL#qb7UE{oHZ)b3@$E&=Sp5`6Rjw'
    '9i`_xJ+bxbnEMZs_6F1c<KqWp2|s2Q@u?2j`}gn5cO)Gw&Qh@OyPcGiDXeW?1=BzR&ixJ_-j^*Jw;GGaGuzwM3-PbbsF_Jei(U0m'
    'nj|-E8{X4>i+<m2B5R$?rI}Lph=sX<@+iZP+`NHB8=92I#_9C}g{XFK6^s0W>3gphPImf71_Rj;Ldi@ZO^yw|J~lJEa-nh<+4#%%'
    '&tE?M`M0M?XPXQ`moJ}qL{Og>gg68<RgJ|#WZm@A#pebo7)MUasQ{kcq*@4#ENUZ32A*Qtb_X}sv0^6{ggGKV`6rQR$d<hpA5=6N'
    '*!<?7_4AIzM;qC;p7U?mgrvL`vfyK}l|cCj#N3G%*RA1H&rgmVp7m%83f=IW1<;}7!C{_zSkqp}!gEj&*<<C2pD%t`UJ8k&m&=uo'
    '7vGS(De4q$k0$pqacI!r9Hw88hg){?q2yy|%9<pW;*`3;5R@Vnrye6$He_hVZss_^ZUyS%{8H>00YNDxZqr6g$0r;_7Kcv0d(k*p'
    'a}!3|6SdN^&EV%9JNZaY((8_5ZQ;OL+I014Gq7jk$KVyjXbw<j$W~gOd=1G9eQj^5AdpIyz!gDUi{_|s$bEp$QL1e=U5f<dTe59~'
    '6M;R#x<UK+?DQztlqoSddG}^(6Se}t^~VmE#-Vdm=<TD$GrA@O!=`?boVEqKtEYbOO6ixYmOE@K2?a2E)w$=ZU6YNA`?K`$2Vj9b'
    'K5olT32^xwl)eFdWXY>ycMrcZb@|VdzOj|`^R1s2@L-e2?PV(Mm8v~-RgHiPE5Nv$8S#?3N`&aV1=0zkaCB3;1WL?r52te^^}QVb'
    'ZBdzZkgfLy?f4wDN?5SmG~FHyv&hbKQZ!cM(bYtux9@PUvz}zCS7&9onWV_}^V<!gQyE1_h$*l%5O80Qv~BHsDbf3unxnymr-kjv'
    ')}C_rC1WAs(8-3AvtcT&ys;Sy3ETG4VqY)XhvIR8i0KtgL0jWxEPw^{L1RNBMapRaUv&_;_*7`vf)s9wEjXoDUa~qM21YA)ZLyl3'
    'YJ`l2u2aH&nac@ck?>F*q6TeF@+!3CiPbW(t897i@_16Jg}n#}nIGJar1F;^5MC!HB|v(gskbQ%Kf%H3BMzyDv2|Yqp3tn6cFX@n'
    '9d_Tg4s&S4qxzg^Z<6d_Ry3D5%zqBi{O#$tkKdk%TRKx?K0agsOTX>DJpHZ*t(H3{9cwM1sP@(jCWn_rC>w~I(nD9}m?!I`C&_bF'
    'HaT3A)iqiDwFo=5zh<gyrn+XTnKD%tXn>A0VWym3mMps(>*<AjN~@C>y{5ElN-Jakq?S{KIMB>FD#g&hX0mH0yJoV#2HYcF{Cqgi'
    ')i3X0L;E;`<vube24|2=$y}vyUvlTc>v6X_qc+ck8CS`!k}n~h>ujpa{m`4qbPa313!m)uTKUUA|JVQf%l`)(y>My'
)))

TURNS_PER_DAY = 24
ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
LAST_STEP = 718
SHED_CAPACITY = 100
MAX_ORDERS = 10
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
WEED_BLOCKED_WORK = {"PLANT", "BUILD_COOP", "BUILD_PASTURE"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}

# Keys are the first two shops in their observed order; values index actions.json.
# All other pairs keep plan 0. Plan 1 is the previous yarn-market continuation.
# Plans 3..12 are the ten distinct continuations selected in the latest search.
SHOP_PLANS = {
    ("BAKERY", "YARN_STORE"): 3,
    ("BRUNCH_SPOT", "YARN_STORE"): 4,
    ("FARMERS_MARKET", "YARN_STORE"): 5,
    ("ICE_CREAM_SHOP", "YARN_STORE"): 6,
    ("PET_CAFE", "YARN_STORE"): 5,
    ("PIZZA_SHOP", "YARN_STORE"): 7,
    ("SMOOTHIE_SHOP", "YARN_STORE"): 8,
    ("YARN_STORE", "BAKERY"): 9,
    ("YARN_STORE", "BRUNCH_SPOT"): 9,
    ("YARN_STORE", "FARMERS_MARKET"): 1,
    ("YARN_STORE", "ICE_CREAM_SHOP"): 9,
    ("YARN_STORE", "PET_CAFE"): 10,
    ("YARN_STORE", "PIZZA_SHOP"): 6,
    ("YARN_STORE", "SMOOTHIE_SHOP"): 11,
    ("YARN_STORE", "YARN_STORE"): 12,
}


class FarmView:
    """Only the current own farm, private inventory, and public prices."""

    def __init__(self, observation):
        farm = observation["farms"][observation["player"]]
        private = observation["private"]
        self.tiles = farm["tiles"]
        self.positions = [farm["farmer"], *farm["hands"]]
        self.inventories = private["inventories"]
        self.shed = {item: max(0, int(qty)) for item, qty in private["shed"].items()}
        self.prices = observation["market"]["prices"]

    def inventory(self, worker):
        return self.inventories[worker] if worker < len(self.inventories) else {}

    def beside_shed(self, position):
        center = len(self.tiles) // 2
        return position[0] in (center - 1, center) and position[1] in (center - 1, center)


class DayState:
    """Per-player memory; queues expire at dawn and sales expire next turn."""

    def __init__(self):
        self.plan = 0
        self.last_step = -1
        self.day = -1
        self.queues = {}
        self.sale_due_step = -1
        self.advanced_sales = {}


def repair_weeds(action, view, state, step):
    """Insert DIG without consuming the blocked action; shift only this worker."""
    day = step // TURNS_PER_DAY
    if day != state.day:
        state.day = day
        state.queues.clear()  # Unfinished work never spills into tomorrow.

    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for worker in range(min(len(workers), len(view.positions))):
        queue = state.queues.setdefault(worker, deque())
        queue.append(list(workers[worker]))
        x, y = view.positions[worker]
        tile = view.tiles[y][x]
        blocked = (queue[0][0] in WEED_BLOCKED_WORK
                   and isinstance(tile, dict) and tile.get("kind") == "WEED")
        workers[worker] = ["DIG"] if blocked else queue.popleft()
    action["farmer"], action["hands"] = workers[0], workers[1:]


def projected_shed(action, view):
    """Estimate stock after this turn's nearby PICKUP, DROP and PLACE actions.

    Preserve worker and inventory order: limited shed capacity can make it matter.
    This is the qualified lightweight estimate, not a full game simulation.
    """
    stock = {item: view.shed.get(item, 0) for item in PRODUCTS}
    stock.update(view.shed)
    total = sum(stock.values())
    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for worker in range(min(len(workers), len(view.positions))):
        if not view.beside_shed(view.positions[worker]):
            continue
        work = workers[worker]
        operation = work[0] if work else "PASS"
        inventory = view.inventory(worker)
        if operation == "PICKUP" and len(work) >= 2 and work[1] in stock:
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            taken = min(stock[work[1]], quantity)
            stock[work[1]] -= taken
            total -= taken
        elif operation == "DROP":
            for item, held in inventory.items():
                added = min(max(0, int(held)), max(0, SHED_CAPACITY - total))
                if added > 0:
                    stock[item] = stock.get(item, 0) + added
                    total += added
        elif operation == "PLACE" and len(work) >= 2 and work[1] not in ANIMALS:
            item = work[1]
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            added = min(quantity, max(0, int(inventory.get(item, 0))),
                        max(0, SHED_CAPACITY - total))
            if added > 0:
                stock[item] = stock.get(item, 0) + added
                total += added
    return stock


def subtract_advanced_sales(action, state, step):
    """Remove quantities already requested one turn early, retaining order slots."""
    if state.sale_due_step == step:
        remaining = dict(state.advanced_sales)
        for order in action["market"]:
            if order and order[0] == "SELL" and len(order) >= 3:
                item = order[1]
                removed = min(max(0, int(order[2])), remaining.get(item, 0))
                if removed > 0:
                    order[2] = int(order[2]) - removed
                    remaining[item] -= removed
    state.advanced_sales = {}
    state.sale_due_step = -1


def advance_sales(action, view, state, tape, step):
    """Bring eligible sales from our next planned action forward by one turn."""
    next_step = step + 1
    if next_step > LAST_STEP or next_step % 72 == 0 or (step % 4 == 0 and step < 144):
        return
    planned = {}
    for order in tape[next_step].get("market") or []:
        if order and order[0] == "SELL" and len(order) >= 3 and order[1] in PRODUCTS:
            item = order[1]
            planned[item] = planned.get(item, 0) + max(0, int(order[2]))
    already_selling = {order[1] for order in action["market"]
                       if order and order[0] == "SELL" and len(order) > 1}
    stock = projected_shed(action, view)
    for item in PRODUCTS:
        if item in ("WHEAT", "FERTILIZER") or item in already_selling:
            continue
        quantity = min(stock.get(item, 0), planned.get(item, 0))
        if quantity <= 0 or int(view.prices.get(item, 0)) < 2:
            continue
        if len(action["market"]) >= MAX_ORDERS:
            break
        action["market"].append(["SELL", item, quantity])
        state.advanced_sales[item] = quantity
    if state.advanced_sales:
        state.sale_due_step = next_step


def liquidate(view):
    """On the last turn, drop reachable inventory and sell the projected shed."""
    workers = [["DROP"] if view.beside_shed(pos) and view.inventory(worker) else ["PASS"]
               for worker, pos in enumerate(view.positions)]
    action = {"farmer": workers[0], "hands": workers[1:], "market": []}
    stock = projected_shed(action, view)
    action["market"] = [["SELL", item, stock[item]] for item in PRODUCTS if stock[item] > 0]
    action["market"].sort(key=lambda order: -int(view.prices.get(order[1], 0)) * order[2])
    return action


class Policy:
    def __init__(self, folder):
        self.tapes = _INLINE_TAPES  # Read-only; each emitted action is copied below.
        if len(self.tapes) != 13 or any(len(tape) != LAST_STEP + 1 for tape in self.tapes):
            raise ValueError("Expected 13 complete, 719-turn action tapes")
        self.players = {}

    def act(self, observation):
        step, player = int(observation["step"]), int(observation["player"])
        state = self.players.get(player)
        if state is None or step <= state.last_step:
            state = self.players[player] = DayState()
        state.last_step = step

        if step == ROUTE_STEP:
            shops = observation["town"]["unlocked_shops"]
            state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)
        if step == FINAL_PLAN_STEP:
            state.plan = 2

        view = FarmView(observation)
        tape = self.tapes[state.plan]
        action = copy.deepcopy(tape[step])
        repair_weeds(action, view, state, step)
        subtract_advanced_sales(action, state, step)
        advance_sales(action, view, state, tape, step)
        action["market"] = action["market"][:MAX_ORDERS]
        return liquidate(view) if step == LAST_STEP else action


_POLICY = None


def agent(observation, configuration=None):
    global _POLICY
    if _POLICY is None:
        _POLICY = Policy(None)
    return _POLICY.act(observation)


# Full Apache license is retained in LICENSE.txt.

# Modified by prvsiyan: V216 adds an observed day-one hiring reserve.
# At most one wheat sale, at step23 only, preserving two projected wheat.
_V216_PARENT=agent
del agent

def agent(observation, configuration=None):
    action=_V216_PARENT(observation,configuration)
    step=int(observation['step'])
    if step!=23 or action.get('market'):
        return action
    player=int(observation['player'])
    state=_POLICY.players[player]
    tape=_POLICY.tapes[state.plan]
    hires=sum(bool(o) and o[0]=='HIRE' for o in tape[24].get('market',[]))
    if not 1<=hires<=5:
        return action
    mult=(configuration or {}).get('farmHandCostMult',1)
    required=sum((1,1,2,3,5)[i] for i in range(hires))*mult
    money=observation['farms'][player]['money']
    view=FarmView(observation)
    if (0<=money<required and projected_shed(action,view).get('WHEAT',0)>=3
            and view.prices.get('WHEAT',0)>=required-money):
        action=copy.deepcopy(action)
        action['market']=[['SELL','WHEAT',1]]
    return action


# Modified by prvsiyan: V217 adds bounded idle-farmer starvation rescue.
# Preserve native pending queues, planned feeds and wheat pickup obligations.
_V217_PARENT=agent
del agent
_V217_MOVES={'EAST':(1,0),'WEST':(-1,0),'NORTH':(0,-1),'SOUTH':(0,1)}

def _v217_farmer(tape, step):
    return list(tape[step].get('farmer') or ['PASS'])

def _v217_plan(view, st, step, action, pending):
    hour = step % 24
    if not 16 <= hour <= 21 or st.get('v217_used', 0) >= 2:
        return None
    if action.get('farmer') != ['PASS']:
        return None
    tape = _POLICY.tapes[st['plan']]
    end = min(step + 24 - hour, 719)
    if len(tape) < end:
        return None
    # Leave every existing planned feeding task intact. This conservative rule
    # also prevents a duplicate rescue when another worker is about to feed.
    reserved_wheat = sum(max(0,int(cmd[2]) if len(cmd)>2 else 1) for cmd in pending if len(cmd)>=2 and cmd[:2]==['PICKUP','WHEAT'])
    for planned in tape[step:end]:
        for cmd in [planned.get('farmer') or []] + list(planned.get('hands') or []):
            if cmd and cmd[0] == 'FEED':
                return None
            if len(cmd) >= 2 and cmd[:2] == ['PICKUP', 'WHEAT']:
                reserved_wheat += max(0, int(cmd[2]) if len(cmd) > 2 else 1)
    start = tuple(view.positions[0])
    inventory = view.inventory(0)
    need_pickup = inventory.get('WHEAT', 0) < 1
    if need_pickup:
        if any(inventory.values()) or not view.beside_shed(start):
            return None
        projected = projected_shed(action, view)
        if projected.get('WHEAT', 0) < max(2, reserved_wheat + 1):
            return None
    targets = []
    for y, row in enumerate(view.tiles):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get('animal') and not tile.get('fed_today') and tile.get('consecutive_unfed', 0) >= 1:
                targets.append((abs(x-start[0])+abs(y-start[1]), y, x))
    for distance, y, x in sorted(targets):
        moves = (['EAST'] * max(0, x-start[0]) + ['WEST'] * max(0, start[0]-x)
                 + ['SOUTH'] * max(0, y-start[1]) + ['NORTH'] * max(0, start[1]-y))
        opposite = {'EAST':'WEST','WEST':'EAST','NORTH':'SOUTH','SOUTH':'NORTH'}
        commands = ([['PICKUP','WHEAT']] if need_pickup else []) + [[m] for m in moves] + [['FEED']] + [[opposite[m]] for m in reversed(moves)]
        if len(commands) > end-step or any(_v217_farmer(tape, step+i) != ['PASS'] for i in range(len(commands))):
            continue
        positions = []
        pos = start
        for cmd in commands:
            positions.append(pos)
            if cmd[0] in _V217_MOVES:
                dx, dy = _V217_MOVES[cmd[0]]
                pos = (pos[0]+dx, pos[1]+dy)
        assert pos == start
        return {'step':step, 'route':st.get('plan'), 'commands':commands,
                'positions':positions, 'target':(x,y)}
    return None


def agent(observation, configuration=None):
    action=_V217_PARENT(observation,configuration)
    step=int(observation['step'])
    player=int(observation['player'])
    state=_POLICY.players[player]
    st=vars(state)
    view=FarmView(observation)
    task=st.get('v217_task')
    if task and step>=task['step']+len(task['commands']):
        task=st['v217_task']=None
    if task is None:
        # Pending work is part of this native router's actual schedule. Avoid
        # displacing the farmer or duplicating a delayed feed from any worker.
        pending=[cmd for queue in state.queues.values() for cmd in queue]
        if state.queues.get(0) or any(cmd and cmd[0]=='FEED' for cmd in pending):
            return action
        task=_v217_plan(view,st,step,action,pending)
        if task:
            st['v217_task']=task
            st['v217_used']=st.get('v217_used',0)+1
    if task is None:
        return action
    offset=step-task['step']
    if (not 0<=offset<len(task['commands']) or tuple(view.positions[0])!=task['positions'][offset]
            or state.plan!=task['route'] or action.get('farmer')!=['PASS']):
        st['v217_task']=None
        return action
    command=task['commands'][offset]
    if command==['FEED']:
        x,y=task['target'];tile=view.tiles[y][x]
        if not isinstance(tile,dict) or not tile.get('animal') or tile.get('fed_today') or view.inventory(0).get('WHEAT',0)<1:
            command=['PASS']
    action=copy.deepcopy(action)
    action['farmer']=command
    return action


# V218: terminal fertilizer collection by up to three otherwise idle workers.
# Inspired by Dmitrii Gluzdov's public Seven-Turn Rescue: collect, return, sell.
# https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800
# This smaller planner searches fertilizer-only trips. Existing productive tasks
# and market orders remain intact; a conservative physical bound rules out shed
# overflow. No future shared price or universal profit guarantee is assumed.
_V218_PARENT=agent
del agent
_V218_REPORT={'plans':0,'planned_units':0,'collections':0,'aborts':0,'capacity_declines':0}

def _v218_path(start, end, tiles):
    x,y=start
    result=[]
    for name,dx,dy,count in [('EAST',1,0,max(0,end[0]-x)),
                             ('WEST',-1,0,max(0,x-end[0])),
                             ('SOUTH',0,1,max(0,end[1]-y)),
                             ('NORTH',0,-1,max(0,y-end[1]))]:
        for _ in range(count):
            x+=dx;y+=dy
            if not (0<=y<len(tiles) and 0<=x<len(tiles[y])) or tiles[y][x]=='LOCKED':
                return None
            result.append([name])
    return result

def _v218_capacity_bound(view):
    total=sum(max(0,int(v)) for v in view.shed.values())
    total+=sum(max(0,int(v)) for inv in view.inventories for v in inv.values())
    for row in view.tiles:
        for tile in row:
            if not isinstance(tile,dict):continue
            total+=int(bool(tile.get('fertilizer_available')))
            if tile.get('animal') or tile.get('crop') in ('TOMATO','STRAWBERRY'):
                total+=max(0,int(tile.get('yield_units',0)))
            elif tile.get('crop'):
                # Absolute fertilized maxima, even for crops that will not be
                # harvested. Within steps712..718 there is no dawn production.
                bound={'WHEAT':12,'CARROT':8,'MELON':12}.get(tile['crop'])
                if bound is None:return 1000000
                total+=bound
    return total

def _v218_routes(start, targets, tiles, sheds):
    by_mask={}
    def visit(pos, mask, commands, count):
        if mask:
            for shed in sheds:
                home=_v218_path(pos,shed,tiles)
                if home is None:continue
                final=commands+home+[['DROP']]
                if len(final)<=7 and (mask not in by_mask or len(final)<len(by_mask[mask]['commands'])):
                    by_mask[mask]={'mask':mask,'count':count,'commands':final}
        if count>=3:return
        for i,target in enumerate(targets):
            if mask&(1<<i):continue
            walk=_v218_path(pos,target,tiles)
            if walk is None:continue
            route=commands+walk+[['COLLECT_FERTILIZER']]
            if len(route)>=7:continue
            if min(abs(target[0]-s[0])+abs(target[1]-s[1]) for s in sheds)+len(route)+1>7:continue
            visit(target,mask|(1<<i),route,count+1)
    visit(start,0,[],0)
    # Bounded search budget. All retained alternatives end with a real DROP.
    options=sorted(by_mask.values(),key=lambda r:(-r['count'],len(r['commands']),r['mask']))[:32]
    return options+[{'mask':0,'count':0,'commands':[]}]

def _v218_plan(observation, action):
    player=int(observation['player'])
    state=_POLICY.players[player]
    if state.plan!=2 or state.last_step!=712:return None
    view=FarmView(observation)
    if view.prices.get('FERTILIZER')!=1:return None
    tape=_POLICY.tapes[state.plan]
    remaining=tape[712:719]
    # No purchases, builds, planting, or fertilizer collection by the parent.
    # This keeps the physical production bound and target ownership simple.
    for planned in remaining:
        if any(o and o[0]!='SELL' for o in planned.get('market',[])):return None
        for c in [planned.get('farmer') or ['PASS']]+list(planned.get('hands') or []):
            if c and c[0] in ('PLANT','BUILD_COOP','BUILD_PASTURE','COLLECT_FERTILIZER'):return None
    if any(c and c[0] in ('PLANT','BUILD_COOP','BUILD_PASTURE','COLLECT_FERTILIZER')
           for queue in state.queues.values() for c in queue):return None
    if _v218_capacity_bound(view)>100:
        _V218_REPORT['capacity_declines']+=1
        return None
    current=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    idle=[]
    for i,pos in enumerate(view.positions):
        if any(view.inventory(i).values()) or state.queues.get(i):continue
        if i<len(current) and current[i]!=['PASS']:continue
        ready=True
        for planned in remaining[:-1]:
            commands=[planned.get('farmer') or ['PASS']]+list(planned.get('hands') or [])
            if i<len(commands) and commands[i]!=['PASS']:ready=False;break
        if ready:idle.append((i,tuple(pos)))
    idle=idle[:3]
    if not idle:return None
    half=len(view.tiles)//2
    sheds=[(x,y) for x,y in ((half-1,half-1),(half,half-1),(half-1,half),(half,half)) if view.tiles[y][x]!='LOCKED']
    targets=[(x,y) for y,row in enumerate(view.tiles) for x,t in enumerate(row)
             if isinstance(t,dict) and t.get('animal') and t.get('fertilizer_available')]
    if not targets or not sheds:return None
    choices=[_v218_routes(pos,targets,view.tiles,sheds) for i,pos in idle]
    best=[(-1,0),[]]
    def choose(index,used,chosen,count,cost):
        if index==len(choices):
            score=(count,-cost)
            if score>best[0]:best[:]=[score,list(chosen)]
            return
        for option in choices[index]:
            if used&option['mask']:continue
            choose(index+1,used|option['mask'],chosen+[option],count+option['count'],cost+len(option['commands']))
    choose(0,0,[],0,0)
    if best[0][0]<=0:return None
    tasks={}
    for (actor,start),option in zip(idle,best[1]):
        if not option['mask']:continue
        commands=option['commands']
        positions=[];pos=start
        for command in commands:
            positions.append(pos)
            if command[0] in _V217_MOVES:
                dx,dy=_V217_MOVES[command[0]];pos=(pos[0]+dx,pos[1]+dy)
        assert pos in sheds and commands[-1]==['DROP']
        tasks[actor]={'commands':commands,'positions':positions}
    _V218_REPORT['plans']+=1
    _V218_REPORT['planned_units']+=best[0][0]
    return tasks

def agent(observation, configuration=None):
    action=_V218_PARENT(observation,configuration)
    step=int(observation['step']);player=int(observation['player'])
    state=_POLICY.players[player]
    if step==712:
        state.v218_tasks=_v218_plan(observation,action)
    tasks=getattr(state,'v218_tasks',None)
    if not tasks or not 712<=step<=718:return action
    view=FarmView(observation)
    commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    commands+=[['PASS'] for _ in range(len(view.positions)-len(commands))]
    for actor,task in list(tasks.items()):
        offset=step-712
        if offset>=len(task['commands']):continue
        if actor>=len(view.positions) or tuple(view.positions[actor])!=task['positions'][offset]:
            del tasks[actor];_V218_REPORT['aborts']+=1;continue
        command=task['commands'][offset]
        if command==['COLLECT_FERTILIZER']:
            x,y=view.positions[actor];tile=view.tiles[y][x]
            if not isinstance(tile,dict) or not tile.get('fertilizer_available'):
                command=['PASS']
            else:_V218_REPORT['collections']+=1
        commands[actor]=command
    action=copy.deepcopy(action)
    action['farmer'],action['hands']=commands[0],commands[1:]
    return action

agent.telemetry=_V218_REPORT


# Appended to frozen V218 by build_v219_tomatoes.py.
# V219: a finite late tomato investment with dedicated, observed workers.
_V219_PARENT = agent
del agent
_V219_FERTILIZE = True  # Builder changes only this flag for the ablation.
_V219_STATES = {}
_V219_REPORT = {'commitments': 0, 'hire_requests': 0, 'confirmed_workers': 0,
                'hire_shortfalls': 0, 'plant_requests': 0, 'confirmed_plants': 0,
                'water_requests': 0, 'fertilize_requests': 0, 'harvest_requests': 0,
                'confirmed_harvest_units': 0, 'drop_requests': 0,
                'tomato_sale_requests': 0, 'budget_declines': 0, 'lost_plants': 0}


def _v219_fib(n):
    a, b = 1, 1
    for _ in range(n): a, b = b, a+b
    return a


def _v219_native_day(native, day):
    tape = _POLICY.tapes[2 if day >= 27 else native.plan]
    return tape[day*24:min((day+1)*24,719)]


def _v219_qualifies(obs, native):
    farm=obs['farms'][obs['player']]
    if len(farm['tiles']) != 10 or set(farm['unlocked_quadrants']) != {'NW','NE','SW'}:
        return False
    if farm['money'] < 12000 or obs['market']['prices']['TOMATO'] < 70:
        return False
    if sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < 3:
        return False
    if any(farm['tiles'][y][x] != 'LOCKED' for y in (5,6) for x in range(5,10)):
        return False
    if obs['private']['seeds'].get('TOMATO',0) or obs['private']['shed'].get('TOMATO',0):
        return False
    if any(isinstance(t,dict) and t.get('crop')=='TOMATO' for row in farm['tiles'] for t in row):
        return False
    # The investment uses spare land and new worker indices. Avoid taking over
    # any native tomato or land purchase obligation on the known own schedule.
    for day in range(18,30):
        for a in _v219_native_day(native,day):
            if any(o and o[0]=='BUY_LAND' for o in a.get('market',[])):return False
            if any(c==['PLANT','TOMATO'] for c in [a.get('farmer')]+a.get('hands',[])):return False
    return True


def _v219_walk(pos, target):
    x,y=pos;tx,ty=target
    if x != tx:return ['EAST' if x < tx else 'WEST']
    if y != ty:return ['SOUTH' if y < ty else 'NORTH']
    return None


def _v219_home(pos):
    return min(((4,4),(5,4),(4,5),(5,5)),key=lambda p:abs(pos[0]-p[0])+abs(pos[1]-p[1]))


def _v219_request(obs, action, state, native):
    step=int(obs['step']);day=step//24;offset=step%24
    farm=obs['farms'][obs['player']];private=obs['private']
    # If the planting-day transaction could not complete, abandon investment.
    # Later purchases would miss the finite day26..29 production window.
    if not state.get('committed') and day!=18:return action
    if state.get('requested_day')==day or offset>3:return action
    planned=_v219_native_day(native,day)
    remaining=planned[offset+1:]
    if any(o and o[0]=='HIRE' for a in remaining for o in a.get('market',[])):
        return action
    parent_hires=sum(bool(o) and o[0]=='HIRE' for o in action['market'])
    expected=max(len(a.get('hands',[])) for a in planned)
    if len(farm['hands'])+parent_hires != expected:return action
    fertilizer=bool(_V219_FERTILIZE and day in (24,27) and obs['market']['prices']['FERTILIZER']<=30)
    # One watering tour: at most 2 entry moves + 9 between tiles + 10 waters.
    # A hire request by hour2 leaves at least21 callbacks after confirmation.
    crop_workers=1 if day in (19,20,21,22,23,25) and offset<=2 else (3 if 26<=day<=28 else 2)
    count=crop_workers+int(fertilizer and day==27)
    extra=[]
    if not state.get('committed'):
        extra += [['BUY_LAND'],['BUY_SEED','TOMATO',10]]
    if fertilizer:extra.append(['BUY_PRODUCT','FERTILIZER',10])
    extra += [['HIRE'] for _ in range(count)]
    if len(action['market'])+len(extra)>MAX_ORDERS:return action
    # No assumed sale proceeds. Reserve 3,000 for parent obligations and price
    # movement; the qualification separately requires 12,000 initial liquidity.
    budget=sum(_v219_fib(n) for n in range(farm['hires_today'],farm['hires_today']+parent_hires+count))
    if not state.get('committed'):budget+=4500
    if fertilizer:budget+=10*(obs['market']['prices']['FERTILIZER']+5)
    for order in action['market']:
        if not order:continue
        if order[0]=='BUY_PRODUCT':budget+=int(order[2])*(int(obs['market']['prices'][order[1]])+10)
        elif order[0]=='BUY_ANIMAL':budget+=int(order[2])*{'COW':400,'SHEEP':500,'GOOSE':300}[order[1]]
        elif order[0]=='BUY_SEED':budget+=int(order[2])*{'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}[order[1]]
    if farm['money']<budget+3000:
        _V219_REPORT['budget_declines']+=1;return action
    state['pending']={'step':step,'first_actor':expected+1,'count':count,'crop_workers':crop_workers,'fertilizer':fertilizer}
    state['requested_day']=day
    _V219_REPORT['hire_requests']+=count
    if not state.get('committed'):
        state['committed']=True;_V219_REPORT['commitments']+=1
    changed=copy.deepcopy(action);changed['market']+=extra
    return changed


def _v219_worker(obs, state, actor, role):
    day=int(obs['step'])//24;step=int(obs['step']);view=FarmView(obs)
    pos=tuple(view.positions[actor]);inv=view.inventory(actor)
    targets=role['targets']
    # Actual cargo differences, observed on the next callback, verify harvests.
    previous=state['last_work'].get(actor)
    if previous and previous['step']==step-1 and previous['command']==['HARVEST']:
        _V219_REPORT['confirmed_harvest_units']+=max(0,int(inv.get('TOMATO',0))-previous['tomatoes'])
    if role.get('needs_fertilizer') and not role.get('loaded'):
        home=_v219_home(pos)
        walk=_v219_walk(pos,home)
        if walk:return walk
        desired=10 if role['kind']=='fertilizer' else 5
        if inv.get('FERTILIZER',0)>=desired:role['loaded']=True
        elif role.get('pickup_requested'):
            # Never spend repeated turns waiting for stock that was not bought.
            role['loaded']=True;role['fertilizer_available']=int(inv.get('FERTILIZER',0))
        elif view.shed.get('FERTILIZER',0)>=desired:
            role['pickup_requested']=True;return ['PICKUP','FERTILIZER',desired]
        else:role['loaded']=True
    todo=[]
    for target in targets:
        x,y=target;tile=view.tiles[y][x]
        tomato=isinstance(tile,dict) and tile.get('crop')=='TOMATO'
        if tomato and target not in state['seen_plants']:
            state['seen_plants'].add(target);_V219_REPORT['confirmed_plants']+=1
        if target in state['seen_plants'] and not tomato and target not in state['lost']:
            state['lost'].add(target);_V219_REPORT['lost_plants']+=1
        command=None
        if role['kind']=='fertilizer':
            if tomato and tile.get('fertilized_until_day',-1)<day+2 and inv.get('FERTILIZER',0)>0:
                command=['FERTILIZE']
        elif day==18 and not tomato:
            if tile is None and obs['private']['seeds'].get('TOMATO',0)>0:command=['PLANT','TOMATO']
            elif isinstance(tile,dict) and tile.get('kind')=='WEED':command=['DIG']
        elif tomato:
            # No later production follows the final day, so watering then would
            # consume time needed to harvest and deliver the final cargo.
            if day<29 and not tile.get('watered_today'):command=['WATER']
            elif role.get('needs_fertilizer') and tile.get('fertilized_until_day',-1)<day+2 and inv.get('FERTILIZER',0)>0:
                command=['FERTILIZE']
            elif tile.get('yield_units',0)>0:command=['HARVEST']
        if command:todo.append((target,command))
    # Final return has priority once only the exact distance plus DROP remains.
    home=_v219_home(pos);distance=abs(pos[0]-home[0])+abs(pos[1]-home[1])
    if step>=718-distance and inv.get('TOMATO',0):
        return _v219_walk(pos,home) or ['PLACE','TOMATO',int(inv.get('TOMATO',0))]
    if todo:
        target,command=min(todo,key=lambda v:(abs(pos[0]-v[0][0])+abs(pos[1]-v[0][1]),targets.index(v[0])))
        return _v219_walk(pos,target) or command
    if inv.get('TOMATO',0):return _v219_walk(pos,home) or ['PLACE','TOMATO',int(inv['TOMATO'])]
    if any(inv.values()):return _v219_walk(pos,home) or ['DROP']
    return ['PASS']


def agent(observation, configuration=None):
    action=_V219_PARENT(observation,configuration)
    step=int(observation['step']);player=int(observation['player']);day=step//24
    state=_V219_STATES.get(player)
    if state is None or step<=state['last_step']:
        state={'last_step':step,'day':-1,'workers':{},'last_work':{},'seen_plants':set(),'lost':set(),
               'targets':[(x,y) for y in (5,6) for x in range(5,10)]}
        _V219_STATES[player]=state
    state['last_step']=step
    native=_POLICY.players[player]
    if step==432:state['eligible']=_v219_qualifies(observation,native)
    if not state.get('eligible') or day<18:return action
    if state['day']!=day:
        state['day']=day;state['workers']={};state['last_work']={}
    farm=observation['farms'][player]
    pending=state.pop('pending',None)
    if pending:
        if len(farm['hands'])+1 >= pending['first_actor']+pending['count'] and 'SE' in farm['unlocked_quadrants']:
            for index in range(pending['count']):
                fertilizer_worker=index==pending['crop_workers']
                if fertilizer_worker:targets=state['targets']
                elif pending['crop_workers']==1:targets=state['targets']
                elif pending['crop_workers']==2:targets=state['targets'][index*5:index*5+5]
                else:targets=[[(5,5),(6,5),(7,5)],[(8,5),(9,5),(9,6),(8,6)],[(5,6),(6,6),(7,6)]][index]
                state['workers'][pending['first_actor']+index]={'kind':'fertilizer' if fertilizer_worker else 'crop','targets':targets,
                    'needs_fertilizer':pending['fertilizer'] and (day==24 or fertilizer_worker)}
            _V219_REPORT['confirmed_workers']+=pending['count']
        else:_V219_REPORT['hire_shortfalls']+=pending['count']
    action=_v219_request(observation,action,state,native)
    if state['workers']:
        commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
        commands += [['PASS'] for _ in range(len(farm['hands'])+1-len(commands))]
        for actor,role in state['workers'].items():
            if actor>=len(commands):continue
            command=_v219_worker(observation,state,actor,role)
            commands[actor]=command
            name={'PLANT':'plant_requests','WATER':'water_requests','FERTILIZE':'fertilize_requests',
                  'HARVEST':'harvest_requests','DROP':'drop_requests'}.get(command[0])
            if name:_V219_REPORT[name]+=1
            state['last_work'][actor]={'step':step,'command':command,'tomatoes':observation['private']['inventories'][actor].get('TOMATO',0)}
        action=copy.deepcopy(action);action['farmer'],action['hands']=commands[0],commands[1:]
    if state.get('committed') and len(action['market'])<MAX_ORDERS and not any(o[:2]==['SELL','TOMATO'] for o in action['market']):
        quantity=projected_shed(action,FarmView(observation)).get('TOMATO',0)
        if quantity>0:
            action=copy.deepcopy(action);action['market'].append(['SELL','TOMATO',quantity])
            _V219_REPORT['tomato_sale_requests']+=quantity
    return action


agent.telemetry=_V219_REPORT

# V221B: labor-only ablation of frozen V219G; not yet publicly scored.

# V224: prioritize already requested sales without crossing same-item purchases.
_V224_PARENT=agent
del agent
_V224_REPORT=dict(_V219_REPORT, reordered_market_turns=0)

def _v224_sales_first(action):
    original=action.get('market',[])[:MAX_ORDERS]
    orders=[list(o) for o in original if o and (o[0] in ('HIRE','BUY_LAND') or (len(o)>=3 and int(o[2])>0))]
    for index in range(len(orders)):
        order=orders[index]
        if order[0]!='SELL':continue
        cursor=index
        while cursor>0:
            previous=orders[cursor-1]
            if previous[0]=='SELL':break
            if previous[0] in ('BUY_PRODUCT','BUY_ANIMAL') and previous[1]==order[1]:break
            orders[cursor-1],orders[cursor]=orders[cursor],orders[cursor-1]
            cursor-=1
    if orders==original:return action
    _V224_REPORT['reordered_market_turns']+=1
    changed=copy.deepcopy(action);changed['market']=orders
    return changed

def agent(observation,configuration=None):
    action=_V224_PARENT(observation,configuration)
    if int(observation['step'])>=144:action=_v224_sales_first(action)
    _V224_REPORT.update(_V219_REPORT)
    return action

agent.telemetry=_V224_REPORT

# V224C: frozen sale timing ablation; no competition rating.

# V226: buy only a bounded shortage in already scheduled next-turn grain pickups.
_V226_PARENT=agent
del agent
_V226_DAY={}
_V226_REPORT=dict(_V224_REPORT, wheat_topup_orders=0, wheat_topup_units=0,
    wheat_topup_budget_declines=0, wheat_topup_capacity_declines=0)


def _v226_topup(obs,action,state,configuration=None):
    step=int(obs['step']);player=int(obs['player'])
    if configuration is not None and any(configuration.get(k,v)!=v for k,v in
        (('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10))):return action
    if not 24<=step<696 or step%24==23 or (step+1)%72==0:return action
    market=action.get('market',[])[:MAX_ORDERS]
    if len(market)>=MAX_ORDERS:return action
    purchases={'HIRE','BUY_LAND','BUY_PRODUCT','BUY_ANIMAL','BUY_SEED'}
    if any(o and (o[0] in purchases or (len(o)>1 and o[1]=='WHEAT')) for o in market):return action
    tape=_POLICY.tapes[state.plan]
    nxt=tape[step+1]
    if any(o and o[0] in purchases for o in nxt.get('market',[])):return action
    view=FarmView(obs);commands=[action.get('farmer') or ['PASS'],*(action.get('hands') or [])]
    future=[nxt.get('farmer') or ['PASS'],*(nxt.get('hands') or [])]
    demand=0
    for actor,pos in enumerate(view.positions):
        current=commands[actor] if actor<len(commands) else ['PASS']
        x,y=pos
        if current and current[0] in _V217_MOVES:
            dx,dy=_V217_MOVES[current[0]];nx,ny=x+dx,y+dy
            if 0<=nx<10 and 0<=ny<10:x,y=nx,ny
        if not view.beside_shed((x,y)):continue
        pending=state.queues.get(actor)
        command=pending[0] if pending else (future[actor] if actor<len(future) else ['PASS'])
        task=vars(state).get('v217_task') if actor==0 else None
        if task:
            offset=step+1-task['step']
            if 0<=offset<len(task['commands']):command=task['commands'][offset]
        if len(command)>=2 and command[:2]==['PICKUP','WHEAT']:
            demand+=max(0,int(command[2]) if len(command)>2 else 1)
    stock=projected_shed(action,view)
    shortage=demand-stock.get('WHEAT',0)
    if not 0<shortage<=4:return action
    day=step//24
    previous=_V226_DAY.get(player)
    if previous is None or previous['day']!=day:
        previous=_V226_DAY[player]={'day':day,'units':0}
    if previous['units']+shortage>8:return action
    if sum(stock.values())+shortage>100:
        _V226_REPORT['wheat_topup_capacity_declines']+=1;return action
    quote=int(obs['market']['prices']['WHEAT'])
    if quote<1 or obs['farms'][player]['money']<100+shortage*(quote+10):
        _V226_REPORT['wheat_topup_budget_declines']+=1;return action
    result=copy.deepcopy(action)
    result['market']=market+[['BUY_PRODUCT','WHEAT',shortage]]
    previous['units']+=shortage
    _V226_REPORT['wheat_topup_orders']+=1;_V226_REPORT['wheat_topup_units']+=shortage
    return result


def agent(observation,configuration=None):
    if int(observation['step'])==0:_V226_DAY.pop(int(observation['player']),None)
    action=_V226_PARENT(observation,configuration)
    state=_POLICY.players[int(observation['player'])]
    action=_v226_topup(observation,action,state,configuration)
    _V226_REPORT.update(_V224_REPORT)
    return action

agent.telemetry=_V226_REPORT

# SPDX-License-Identifier: Apache-2.0
"""Bounded sale reservation across the next two or three known own actions.

Modified 2026-09-10 by Dmitrii Gluzdov. Extends the one-turn advancement in
yhay81 / aurax7 / prvsiyan's router, without reading future market observations.
This module is appended to the audited Moon policy during development staging.
"""

SALE_HORIZON = 3
ADVANCE_START = 288
_SALE_NATIVE_ADVANCE = advance_sales
_SALE_NATIVE_SUBTRACT = subtract_advanced_sales



def subtract_advanced_sales(action, state, step):
    # The opening finances land and the full herd. Preserve the parent's exact
    # behavior through day11, including any one-turn reservation due at288.
    if step < ADVANCE_START:
        return _SALE_NATIVE_SUBTRACT(action, state, step)
    if state.sale_due_step == step:
        _SALE_NATIVE_SUBTRACT(action, state, step)
    debts = getattr(state, 'sale_window_debts', {})
    due = debts.pop(step, {})
    for order in action['market']:
        if len(order) >= 3 and order[0] == 'SELL':
            removed = min(max(0, int(order[2])), due.get(order[1], 0))
            order[2] = int(order[2]) - removed
            due[order[1]] = due.get(order[1], 0) - removed
    state.sale_window_debts = {k: v for k, v in debts.items() if k > step}
    state.advanced_sales = {}
    state.sale_due_step = -1


def reserve_sales(action, view, state, tape, step):
    horizon = SALE_HORIZON if step >= 144 else 1
    if step < 144 and step % 4 == 0:
        return
    # Do not cross a route/shop boundary; its new plan is not chosen yet.
    end = min(LAST_STEP, step + horizon, (step // 72 + 1) * 72 - 1)
    if end <= step:
        return
    market = action['market']
    stock = projected_shed(action, view)
    blocked = {o[1] for o in market if len(o) > 1 and o[0] in ('SELL', 'BUY_PRODUCT')}
    blocked.update(c[1] for queue in state.queues.values() for c in queue
                   if len(c) > 1 and c[0] == 'PICKUP')
    blocked.update(c[1] for c in [action.get('farmer') or ['PASS'], *(action.get('hands') or [])]
                   if len(c) > 1 and c[0] == 'PICKUP')
    # Animal PLACE may fall back into the shed; the inherited projection does
    # not model it. Retain conservative no-advancement behavior in that case.
    commands = [action.get('farmer') or ['PASS'], *(action.get('hands') or [])]
    if any(len(c) > 1 and c[0] == 'PLACE' and c[1] in ANIMALS
           and view.inventory(i).get(c[1], 0) > 0 for i, c in enumerate(commands)):
        return
    debts = getattr(state, 'sale_window_debts', {})
    for item in PRODUCTS:
        if item in ('WHEAT', 'FERTILIZER') or item in blocked or view.prices.get(item, 0) < 2:
            continue
        available = max(0, int(stock.get(item, 0)))
        if not available or len(market) >= MAX_ORDERS:
            continue
        reservations = []
        for due_step in range(step + 1, end + 1):
            future = tape[due_step]
            # Preserve upcoming stock consumers, not just today's inventory.
            work = [future.get('farmer') or ['PASS'], *(future.get('hands') or [])]
            if any(len(c) > 1 and c[0] == 'PICKUP' and c[1] == item for c in work):
                break
            if any(len(o) > 1 and o[0] == 'BUY_PRODUCT' and o[1] == item for o in future.get('market', [])):
                break
            planned = sum(max(0, int(o[2])) for o in future.get('market', [])
                          if len(o) >= 3 and o[:2] == ['SELL', item])
            remaining = max(0, planned - debts.get(due_step, {}).get(item, 0))
            amount = min(available, remaining)
            if amount:
                reservations.append((due_step, amount))
                available -= amount
            if not available:
                break
        quantity = sum(amount for _, amount in reservations)
        if quantity:
            market.append(['SELL', item, quantity])
            for due_step, amount in reservations:
                debt = debts.setdefault(due_step, {})
                debt[item] = debt.get(item, 0) + amount
    state.sale_window_debts = debts


def advance_sales(action, view, state, tape, step):
    if step < ADVANCE_START:
        return _SALE_NATIVE_ADVANCE(action, view, state, tape, step)
    # The inherited call is before the tomato/fertilizer worker repairs. Defer
    # advancement until their final commands are available for stock projection.
    return None


_SALE_PARENT = agent


def agent(observation, configuration=None):
    action = _SALE_PARENT(observation, configuration)
    step = int(observation['step'])
    if step < ADVANCE_START or step >= LAST_STEP:
        return action
    state = _POLICY.players[int(observation['player'])]
    reserve_sales(action, FarmView(observation), state, _POLICY.tapes[state.plan], step)
    if step >= 144:
        action = _v224_sales_first(action)
    return action


agent.telemetry = _SALE_PARENT.telemetry


# Development benchmarking can drain these events; the agent requires no logger.
_SUBMISSION_SALE_EVENTS = []
_SUBMISSION_RESERVE = reserve_sales

def reserve_sales(action, view, state, tape, step):
    before = len(action['market'])
    _SUBMISSION_RESERVE(action, view, state, tape, step)
    for order in action['market'][before:]:
        _SUBMISSION_SALE_EVENTS.append({'type': 'strategy_decision',
            'hypothesis': 'sale_horizon', 'turn': step, 'horizon': 3,
            'item': order[1], 'quantity': order[2]})

def drain_telemetry():
    events = list(_SUBMISSION_SALE_EVENTS)
    _SUBMISSION_SALE_EVENTS.clear()
    return events

# Preserved upstream licensing and attribution.
LICENSE_TEXT = '\n                                 Apache License\n                           Version 2.0, January 2004\n                        http://www.apache.org/licenses/\n\n   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION\n\n   1. Definitions.\n\n      "License" shall mean the terms and conditions for use, reproduction,\n      and distribution as defined by Sections 1 through 9 of this document.\n\n      "Licensor" shall mean the copyright owner or entity authorized by\n      the copyright owner that is granting the License.\n\n      "Legal Entity" shall mean the union of the acting entity and all\n      other entities that control, are controlled by, or are under common\n      control with that entity. For the purposes of this definition,\n      "control" means (i) the power, direct or indirect, to cause the\n      direction or management of such entity, whether by contract or\n      otherwise, or (ii) ownership of fifty percent (50%) or more of the\n      outstanding shares, or (iii) beneficial ownership of such entity.\n\n      "You" (or "Your") shall mean an individual or Legal Entity\n      exercising permissions granted by this License.\n\n      "Source" form shall mean the preferred form for making modifications,\n      including but not limited to software source code, documentation\n      source, and configuration files.\n\n      "Object" form shall mean any form resulting from mechanical\n      transformation or translation of a Source form, including but\n      not limited to compiled object code, generated documentation,\n      and conversions to other media types.\n\n      "Work" shall mean the work of authorship, whether in Source or\n      Object form, made available under the License, as indicated by a\n      copyright notice that is included in or attached to the work\n      (an example is provided in the Appendix below).\n\n      "Derivative Works" shall mean any work, whether in Source or Object\n      form, that is based on (or derived from) the Work and for which the\n      editorial revisions, annotations, elaborations, or other modifications\n      represent, as a whole, an original work of authorship. For the purposes\n      of this License, Derivative Works shall not include works that remain\n      separable from, or merely link (or bind by name) to the interfaces of,\n      the Work and Derivative Works thereof.\n\n      "Contribution" shall mean any work of authorship, including\n      the original version of the Work and any modifications or additions\n      to that Work or Derivative Works thereof, that is intentionally\n      submitted to Licensor for inclusion in the Work by the copyright owner\n      or by an individual or Legal Entity authorized to submit on behalf of\n      the copyright owner. For the purposes of this definition, "submitted"\n      means any form of electronic, verbal, or written communication sent\n      to the Licensor or its representatives, including but not limited to\n      communication on electronic mailing lists, source code control systems,\n      and issue tracking systems that are managed by, or on behalf of, the\n      Licensor for the purpose of discussing and improving the Work, but\n      excluding communication that is conspicuously marked or otherwise\n      designated in writing by the copyright owner as "Not a Contribution."\n\n      "Contributor" shall mean Licensor and any individual or Legal Entity\n      on behalf of whom a Contribution has been received by Licensor and\n      subsequently incorporated within the Work.\n\n   2. Grant of Copyright License. Subject to the terms and conditions of\n      this License, each Contributor hereby grants to You a perpetual,\n      worldwide, non-exclusive, no-charge, royalty-free, irrevocable\n      copyright license to reproduce, prepare Derivative Works of,\n      publicly display, publicly perform, sublicense, and distribute the\n      Work and such Derivative Works in Source or Object form.\n\n   3. Grant of Patent License. Subject to the terms and conditions of\n      this License, each Contributor hereby grants to You a perpetual,\n      worldwide, non-exclusive, no-charge, royalty-free, irrevocable\n      (except as stated in this section) patent license to make, have made,\n      use, offer to sell, sell, import, and otherwise transfer the Work,\n      where such license applies only to those patent claims licensable\n      by such Contributor that are necessarily infringed by their\n      Contribution(s) alone or by combination of their Contribution(s)\n      with the Work to which such Contribution(s) was submitted. If You\n      institute patent litigation against any entity (including a\n      cross-claim or counterclaim in a lawsuit) alleging that the Work\n      or a Contribution incorporated within the Work constitutes direct\n      or contributory patent infringement, then any patent licenses\n      granted to You under this License for that Work shall terminate\n      as of the date such litigation is filed.\n\n   4. Redistribution. You may reproduce and distribute copies of the\n      Work or Derivative Works thereof in any medium, with or without\n      modifications, and in Source or Object form, provided that You\n      meet the following conditions:\n\n      (a) You must give any other recipients of the Work or\n          Derivative Works a copy of this License; and\n\n      (b) You must cause any modified files to carry prominent notices\n          stating that You changed the files; and\n\n      (c) You must retain, in the Source form of any Derivative Works\n          that You distribute, all copyright, patent, trademark, and\n          attribution notices from the Source form of the Work,\n          excluding those notices that do not pertain to any part of\n          the Derivative Works; and\n\n      (d) If the Work includes a "NOTICE" text file as part of its\n          distribution, then any Derivative Works that You distribute must\n          include a readable copy of the attribution notices contained\n          within such NOTICE file, excluding those notices that do not\n          pertain to any part of the Derivative Works, in at least one\n          of the following places: within a NOTICE text file distributed\n          as part of the Derivative Works; within the Source form or\n          documentation, if provided along with the Derivative Works; or,\n          within a display generated by the Derivative Works, if and\n          wherever such third-party notices normally appear. The contents\n          of the NOTICE file are for informational purposes only and\n          do not modify the License. You may add Your own attribution\n          notices within Derivative Works that You distribute, alongside\n          or as an addendum to the NOTICE text from the Work, provided\n          that such additional attribution notices cannot be construed\n          as modifying the License.\n\n      You may add Your own copyright statement to Your modifications and\n      may provide additional or different license terms and conditions\n      for use, reproduction, or distribution of Your modifications, or\n      for any such Derivative Works as a whole, provided Your use,\n      reproduction, and distribution of the Work otherwise complies with\n      the conditions stated in this License.\n\n   5. Submission of Contributions. Unless You explicitly state otherwise,\n      any Contribution intentionally submitted for inclusion in the Work\n      by You to the Licensor shall be under the terms and conditions of\n      this License, without any additional terms or conditions.\n      Notwithstanding the above, nothing herein shall supersede or modify\n      the terms of any separate license agreement you may have executed\n      with Licensor regarding such Contributions.\n\n   6. Trademarks. This License does not grant permission to use the trade\n      names, trademarks, service marks, or product names of the Licensor,\n      except as required for reasonable and customary use in describing the\n      origin of the Work and reproducing the content of the NOTICE file.\n\n   7. Disclaimer of Warranty. Unless required by applicable law or\n      agreed to in writing, Licensor provides the Work (and each\n      Contributor provides its Contributions) on an "AS IS" BASIS,\n      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or\n      implied, including, without limitation, any warranties or conditions\n      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A\n      PARTICULAR PURPOSE. You are solely responsible for determining the\n      appropriateness of using or redistributing the Work and assume any\n      risks associated with Your exercise of permissions under this License.\n\n   8. Limitation of Liability. In no event and under no legal theory,\n      whether in tort (including negligence), contract, or otherwise,\n      unless required by applicable law (such as deliberate and grossly\n      negligent acts) or agreed to in writing, shall any Contributor be\n      liable to You for damages, including any direct, indirect, special,\n      incidental, or consequential damages of any character arising as a\n      result of this License or out of the use or inability to use the\n      Work (including but not limited to damages for loss of goodwill,\n      work stoppage, computer failure or malfunction, or any and all\n      other commercial damages or losses), even if such Contributor\n      has been advised of the possibility of such damages.\n\n   9. Accepting Warranty or Additional Liability. While redistributing\n      the Work or Derivative Works thereof, You may choose to offer,\n      and charge a fee for, acceptance of support, warranty, indemnity,\n      or other liability obligations and/or rights consistent with this\n      License. However, in accepting such obligations, You may act only\n      on Your own behalf and on Your sole responsibility, not on behalf\n      of any other Contributor, and only if You agree to indemnify,\n      defend, and hold each Contributor harmless for any liability\n      incurred by, or claims asserted against, such Contributor by reason\n      of your accepting any such warranty or additional liability.\n\n   END OF TERMS AND CONDITIONS\n\n   APPENDIX: How to apply the Apache License to your work.\n\n      To apply the Apache License to your work, attach the following\n      boilerplate notice, with the fields enclosed by brackets "[]"\n      replaced with your own identifying information. (Don\'t include\n      the brackets!)  The text should be enclosed in the appropriate\n      comment syntax for the file format. We also recommend that a\n      file or class name and description of purpose be included on the\n      same "printed page" as the copyright notice for easier\n      identification within third-party archives.\n\n   Copyright [yyyy] [name of copyright owner]\n\n   Licensed under the Apache License, Version 2.0 (the "License");\n   you may not use this file except in compliance with the License.\n   You may obtain a copy of the License at\n\n       http://www.apache.org/licenses/LICENSE-2.0\n\n   Unless required by applicable law or agreed to in writing, software\n   distributed under the License is distributed on an "AS IS" BASIS,\n   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n   See the License for the specific language governing permissions and\n   limitations under the License.\n'
NOTICE_TEXT = "E184 Sale Window, modified September 10, 2026 by Dmitrii Gluzdov.\nParent: prvsiyan, Kaggriculture Frontier | The Moon Counts Melons, public v37.\nhttps://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-the-moon-counts-melons\nOriginal 13 production tapes: yhay81, Shop Router 0909.\nhttps://www.kaggle.com/code/yhay81/shop-router-0909\nSale timing and shed projection credit: aurax7, Reactive Router.\nhttps://www.kaggle.com/code/aurax7/kaggriculture-reactive-router\nParent terminal collection credits Dmitrii Gluzdov's Seven-Turn Rescue.\nAll original in-source author notices are retained. Apache License 2.0.\n\nChanges: sale reservations across two or three known future own actions;\nper-due-step debt avoids counting an advanced sale twice; stock projection\nruns after all worker repairs; queue, consumer, capacity and route-boundary\nguards. Routes, feed and crop-investment logic remain inherited.\nPackaging: inline route JSON restored as actions.json, complete license moved\nfrom comments to LICENSE.txt; executable source remains readable, uncompressed.\n"

# Kaggle chooses the last inserted callable in the executed namespace.
_KAGGLE_ENTRYPOINT = agent
