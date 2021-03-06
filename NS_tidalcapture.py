import numpy as np 
import os,sys
from collections import Counter
import re
import gzip

import scripts
import scripts1
import scripts2
import scripts3
import dynamics as dyn
import unit_convert as uc
import ecc_calc as gwcalc
import LISA_calculations as lisa
import ns_history as nh

yearsc=31557600.
twopi=6.283185307179586
Gconst=6.674*10**-8 ##cm3*g-1*s-2
clight=3*10**10 ##cm/s
Msun=2*10**33 ##gram
AU=1.496*10**13  ##cm
PC=3.086*10**18  ##cm
Kconst=9.87*10**-48 ##yr/G^2
Lsun=4.02*10**16 ##mJy*kpc^2


##Types of tidal captures in the tidal capture file
def find_tc_properties(filepath):
    filestr=filepath+'initial'
    tcfile=filestr+'.tidalcapture.log'
    t=[]; id0=[]; id1=[]; m0=[]; m1=[]; k0=[]; k1=[]; a=[]; e=[]
    with open(tcfile, 'r') as ftc:
        next(ftc)
        for line in ftc:
            data=line.split()
            t.append(float(data[0]))
            numstr=re.findall(r"\d*\.\d+|\d+", data[2])
            id0.append(int(numstr[6])); id1.append(int(numstr[11]))
            m0.append(float(numstr[7])); m1.append(float(numstr[12]))
            k0.append(int(numstr[8])); k1.append(int(numstr[13]))
            a.append(float(numstr[9])); e.append(float(numstr[10]))

    return id0, id1, m0, m1, k0, k1, a, e, t


##Find how many tidal capture binaries have become NS binaries
def find_tc_ns(filepath, savepath):
    ID0, ID1, M0, M1, K0, K1, A, E, T = find_tc_properties(filepath)
    filestr=filepath+'initial'
    psrfile=filestr+'.morepulsars.dat'

    f1=open(savepath+'tc_binarypsr.dat', 'a+')##The tc binary is intact and one of the stars becomes a NS
    f2=open(savepath+'tc_singlepsr.dat', 'a+')##The tc binary is not intact but one of the stars becomes a NS
    f1.write('#1.Time 2.ID0 3.ID1 4.M0 5.M1 6.K0 7.K1 8.A(AU) 9.ECC 10.B0 11.B1 12.P0 13.P1\n')
    f2.write('#1.Time 2.ID0 3.ID1 4.M0 5.M1 6.K0 7.K1 8.A(AU) 9.ECC 10.B0 11.B1 12.P0 13.P1\n')
    for i in range(len(ID0)):
        check0=0; check1=0
        with open(psrfile, 'r') as fpsr:
            next(fpsr)
            for line in fpsr:
                datapsr=line.split()
                if float(datapsr[1])>T[i]:
                    if (int(datapsr[3])==ID0[i] and int(datapsr[4])==ID1[i]) or (int(datapsr[3])==ID1[i] and int(datapsr[4])==ID0[i]):
                        f1.write('%f %d %d %f %f %d %d %f %f %e %e %f %f\n'%(float(datapsr[1]), int(datapsr[3]), int(datapsr[4]), float(datapsr[5]), float(datapsr[6]), int(datapsr[11]), int(datapsr[12]), float(datapsr[13]), float(datapsr[14]), float(datapsr[7]), float(datapsr[8]), float(datapsr[9]), float(datapsr[10])))
                        break

                    elif check0==0 and (int(datapsr[3])==ID0[i] or int(datapsr[4])==ID0[i]):
                        f2.write('%f %d %d %f %f %d %d %f %f %e %e %f %f\n'%(float(datapsr[1]), int(datapsr[3]), int(datapsr[4]), float(datapsr[5]), float(datapsr[6]), int(datapsr[11]), int(datapsr[12]), float(datapsr[13]), float(datapsr[14]), float(datapsr[7]), float(datapsr[8]), float(datapsr[9]), float(datapsr[10])))
                        check0=1


                    elif check1==0 and (int(datapsr[3])==ID1[i] and int(datapsr[4])==ID1[i]):
                        f2.write('%f %d %d %f %f %d %d %f %f %e %e %f %f\n'%(float(datapsr[1]), int(datapsr[3]), int(datapsr[4]), float(datapsr[5]), float(datapsr[6]), int(datapsr[11]), int(datapsr[12]), float(datapsr[13]), float(datapsr[14]), float(datapsr[7]), float(datapsr[8]), float(datapsr[9]), float(datapsr[10])))
                        check1=0

                if check0==1 and check1==1: break

        print(i)

    f1.close()
    f2.close()


##Find tc binaries or singles that are still pulsars at the end
def find_tc_psr():
    data_tcbin=np.genfromtxt('/projects/b1095/syr904/projects/PULSAR2/tc_comparison/tc_binarypsr.dat')
    data_tcsin=np.genfromtxt('/projects/b1095/syr904/projects/PULSAR2/tc_comparison/tc_singlepsr.dat')
    data_msp=np.genfromtxt('/projects/b1095/syr904/projects/PULSAR2/tc_comparison/MSP_last.dat')
    data_psr=np.genfromtxt('/projects/b1095/syr904/projects/PULSAR2/tc_comparison/PSR_last.dat')

    id_tcbin=[]; id_tcsin=[]; id_msp=[]; id_psr=[]

    id0_tc=np.concatenate((data_tcbin[:,1],data_tcsin[:,1]))
    id1_tc=np.concatenate((data_tcbin[:,2],data_tcsin[:,2]))
    id_psrs=np.concatenate((data_msp[:,12],data_psr[:,12]))

    print(np.intersect1d(id0_tc, id_psrs))
    print(np.intersect1d(id1_tc, id_psrs))



##Find NS-MS star binaries at the last snapshot and check if they are formed in tidal capture
def find_NS_MS_last(filepath, savepath):
    ID0, ID1, M0, M1, K0, K1, A, E, T = find_tc_properties(filepath)

    filestr=filepath+'initial'
    snaps=dyn.get_snapshots(filestr)
    lastsnap=snaps[-1]
    t_conv=dyn.conv('t', filestr+'.conv.sh')
    time=dyn.get_time(lastsnap)*t_conv
    model=1
    
    fmsb=open(savepath+'NS_MS_last.dat', 'a+')
    fmsb.write('#1.Model 2.Time 3.ID0 4.ID1 5.M0 6.M1 7.K0 8.K1 9.a(AU) 10.ecc 11.radrol0 12.radrol1 13.B(G) 14.P(sec) 15.tcflag\n')

    with gzip.open(lastsnap, 'r') as flast:
        next(flast); next(flast)
        for line in flast:
            datalast=line.split()
            if int(datalast[7])==1:
                if int(datalast[17])==13 and 0<=int(datalast[18])<=1:
                    ID0ms=int(datalast[10]); ID1ms=int(datalast[11])
                    if (ID0ms in ID0 and ID1ms in ID1) or (ID1ms in ID0 and ID0ms in ID1):
                        tcflag=1
                    elif ID0ms in ID0 or ID0ms in ID1:
                        tcflag=2
                    else:
                        tcflag=3

                    fmsb.write('%d %f %d %d %f %f %d %d %f %f %f %f %e %f %d\n'%(model, time, int(datalast[10]), int(datalast[11]), float(datalast[8]), float(datalast[9]), int(datalast[17]), int(datalast[18]), float(datalast[12]), float(datalast[13]), float(datalast[43]), float(datalast[44]), float(datalast[47]), float(twopi*yearsc/float(datalast[45])), tcflag))


                if 0<=int(datalast[17])<=1 and int(datalast[18])==13:
                    ID0ms=int(datalast[11]); ID1ms=int(datalast[10])
                    if (ID0ms in ID0 and ID1ms in ID1) or (ID1ms in ID0 and ID0ms in ID1):
                        tcflag=1
                    elif ID0ms in ID0 or ID0ms in ID1:
                        tcflag=2
                    else:
                        tcflag=3

                    fmsb.write('%d %f %d %d %f %f %d %d %f %f %f %f %e %f %d\n'%(model, time, int(datalast[11]), int(datalast[10]), float(datalast[9]), float(datalast[8]), int(datalast[18]), int(datalast[17]), float(datalast[13]), float(datalast[12]), float(datalast[44]), float(datalast[43]), float(datalast[48]), float(twopi*yearsc/float(datalast[46])), tcflag))

    fmsb.close()

##Find NS-MS star binaries at all times and check if they are formed in tidal capture
def find_NSMS_atalltime(filepath, savepath):
    ID0, ID1, M0, M1, K0, K1, A, E, T = find_tc_properties(filepath)

    filestr=filepath+'initial'
    t_conv=dyn.conv('t', filestr+'.conv.sh')
    l_conv=dyn.conv('l', filestr+'.conv.sh')
    
    fnsms=open(savepath+'/NS_MS_alltimes.dat', 'w+')
    fnsms.write('#1:TotalTime(Myr) 2:id0 3:id1 4:m0[MSUN] 5:m1[MSUN] 6:B[G] 7:P[sec] 8:startype0 9:startype1 10:Porb(days) 11:ecc 12:radrol0 13:radrol1 14:r 15:tcflag 16:rbflag\n')

    fnsms_selected=open(savepath+'/rb_progenitor_alltimes.dat', 'w+')
    fnsms_selected.write('#1:TotalTime(Myr) 2:id0 3:id1 4:m0[MSUN] 5:m1[MSUN] 6:B[G] 7:P[sec] 8:startype0 9:startype1 10:Porb(days) 11:ecc 12:radrol0 13:radrol1 14:r 15:tcflag 16:rbflag\n')
    with open(filestr+'.morepulsars.dat', 'r') as fpsr:
        next(fpsr)
        for line in fpsr:
            data=line.split()
            if int(data[2])==1:
                if int(data[11])==13 and int(data[12])<=1:
                    if (int(data[3]) in ID0 and int(data[4]) in ID1) or (int(data[4]) in ID0 and int(data[3]) in ID1):
                        tcflag=1
                    elif int(data[3]) in ID0 or int(data[3]) in ID1:
                        tcflag=2
                    else:
                        tcflag=3

                    porb=uc.au_to_period(float(data[13]), float(data[5]), float(data[6]))
                    if float(data[6])<=2.0 and porb<=2.0:
                        rbflag=1
                    else:
                        rbflag=0

                    fnsms.write('%f %d %d %f %f %e %f %d %d %f %f %f %f %f %d %d\n'%(float(data[1])*t_conv, int(data[3]), int(data[4]), float(data[5]), float(data[6]), float(data[7]), float(data[9]), int(data[11]), int(data[12]), porb, float(data[14]), float(data[15]), float(data[16]), float(data[19])*l_conv, tcflag, rbflag))

                    if rbflag==1:
                        fnsms_selected.write('%f %d %d %f %f %e %f %d %d %f %f %f %f %f %d %d\n'%(float(data[1])*t_conv, int(data[3]), int(data[4]), float(data[5]), float(data[6]), float(data[7]), float(data[9]), int(data[11]), int(data[12]), porb, float(data[14]), float(data[15]), float(data[16]), float(data[19])*l_conv, tcflag, rbflag))


                if int(data[12])==13 and int(data[11])<=1:
                    if (int(data[3]) in ID0 and int(data[4]) in ID1) or (int(data[4]) in ID0 and int(data[3]) in ID1):
                        tcflag=1
                    elif int(data[4]) in ID0 or int(data[4]) in ID1:
                        tcflag=2
                    else:
                        tcflag=3

                    porb=uc.au_to_period(float(data[13]), float(data[5]), float(data[6]))
                    if float(data[5])<=2.0 and porb<=2.0:
                        rbflag=1
                    else:
                        rbflag=0

                    fnsms.write('%f %d %d %f %f %e %f %d %d %f %f %f %f %f %d %d\n'%(float(data[1])*t_conv, int(data[4]), int(data[3]), float(data[6]), float(data[5]), float(data[8]), float(data[10]), int(data[12]), int(data[11]), porb, float(data[14]), float(data[16]), float(data[15]), float(data[19])*l_conv, tcflag, rbflag))

                    if rbflag==1:
                       fnsms_selected.write('%f %d %d %f %f %e %f %d %d %f %f %f %f %f %d %d\n'%(float(data[1])*t_conv, int(data[4]), int(data[3]), float(data[6]), float(data[5]), float(data[8]), float(data[10]), int(data[12]), int(data[11]), porb, float(data[14]), float(data[16]), float(data[15]), float(data[19])*l_conv, tcflag, rbflag)) 

    fnsms.close()
    fnsms_selected.close()



##Find the unique rb progenitors at their first and last timesteps from the rb_progenitor_alltimes.dat file
def find_rbprogen_Unique(savepath, modelpath):
    data=np.genfromtxt(savepath+'rb_progenitor_alltimes.dat')
    times=data[:,0]; id0=data[:,1]; id1=data[:,2]
    alltimes=list(Counter(times).keys())
    #print(len(alltimes))

    id0_unique_end=[]; id1_unique_end=[]; time_unique_end=[]
    idstr_hold1_end=[str(0)]
    idstr_hold2_end=[str(0)]
    for i in range(len(alltimes)-1, 0, -1):
        timeno=alltimes[i]

        for j in range(len(times)-1, 0, -1):
            if times[j]==timeno:
                idstr=str(int(id0[j]))+str(int(id1[j]))
                check=1
                for k in range(len(idstr_hold1_end)):
                    if idstr==idstr_hold1_end[k] or idstr==idstr_hold2_end[k]:
                        check=0
    
                if check==1:
                    time_unique_end.append(times[j]); id0_unique_end.append(id0[j]); id1_unique_end.append(id1[j])

                    idstr_hold1_end.append(idstr)
                    idstr_hold2_end.append(str(int(id1[j]))+str(int(id0[j])))

        #print(i)
    print(id0_unique_end)

    id0_unique_begin=[]; id1_unique_begin=[]; time_unique_begin=[]
    idstr_hold1_begin=[str(0)]
    idstr_hold2_begin=[str(0)]
    for i in range(len(alltimes)):
        timeno=alltimes[i]

        for j in range(len(times)):
            if times[j]==timeno:
                idstr=str(int(id0[j]))+str(int(id1[j]))
                check=1
                for k in range(len(idstr_hold1_begin)):
                    if idstr==idstr_hold1_begin[k] or idstr==idstr_hold2_begin[k]:
                        check=0
    
                if check==1:
                    time_unique_begin.append(times[j]); id0_unique_begin.append(id0[j]); id1_unique_begin.append(id1[j])

                    idstr_hold1_begin.append(idstr)
                    idstr_hold2_begin.append(str(int(id1[j]))+str(int(id0[j])))
    print(id0_unique_begin)

    funique=open(savepath+'rb_prog_unique.dat', 'w+')
    funique.write('#1:TotalTime(Myr) 2:id0 3:id1 4:m0[MSUN] 5:m1[MSUN] 6:B[G] 7:P[sec] 8:startype0 9:startype1 10:Porb(days) 11:ecc 12:radrol0 13:radrol1 14:r 15:tcflag 16:rbflag 17.Formation 18.Disruption 29.Nenc\n')
    frball=open(savepath+'rb_progenitor_alltimes.dat', 'r')
    datarball=frball.readlines()
    #print(datarball)

    for m in range(len(id0_unique_begin)):
        for x in range(1, len(datarball)):
            data=datarball[x].split()
            if float(data[0])==time_unique_begin[m] and int(data[1])==id0_unique_begin[m] and int(data[2])==id1_unique_begin[m]:
                theline=datarball[x].strip('\n')+' '+str(-100)+' '+str(-100)+' '+str(-100)+'\n'
                funique.write(theline)
                print(time_unique_begin[m])

        for n in range(len(id0_unique_end)):
            if id0_unique_begin[m]==id0_unique_end[n]:
                print(id0_unique_begin[m], id0_unique_end[n])
                disruption=nh.find_binary_disruipt(id0_unique_begin[m], id1_unique_begin[m], modelpath)
                formation=nh.find_binary_form(id0_unique_begin[m], id1_unique_begin[m], modelpath)
                any_enc=nh.find_binary_encounter(id0_unique_begin[m], id1_unique_begin[m], modelpath, [time_unique_begin[m], time_unique_end[n]])
                for x in range(1, len(datarball)):
                    data=datarball[x].split()
                    if float(data[0])==time_unique_end[n] and int(data[1])==id0_unique_end[n] and int(data[2])==id1_unique_end[n]:
                        theline=datarball[x].strip('\n')+' '+formation+' '+disruption+' '+any_enc+'\n'
                        funique.write(theline)
    
    frball.close()
    funique.close()



##Find NS-MS binaries that contain a MSP in many models
def find_msp_NSMS_9to14Gyr(savepath):
    data=np.genfromtxt(savepath+'msp_9to14Gyr.dat')
    model=data[:,0]; id0=data[:,12]; id1=data[:,13]; k0=data[:,14]; k1=data[:,15]
    model_unique=list(Counter(model).keys())

    f_all=open(savepath+'msp_9to14Gyr.dat')
    data_all=f_all.readlines()


    #f=open(savepath+'msp_nsms_9to14Gyr.dat', 'w+')
    #f.write('#1.Model 2.Time(Myr) 3.Status 4.r(pc) 5.B(G) 6.P(sec) 7.dmdt0(Msun/yr) 8.dmdt1(Msun/yr) 9.rolrad0 10.rolrad1 11.m0(Msun) 12.m1(Msun) 13.ID0 14.ID1 15.k0 16.k1 17.a(AU) 18.ecc 19.Formation\n')
    #for i in range(1, len(data_all)):
    #    line=data_all[i].split()
    #    if int(line[14])==13 and 0<=int(line[15])<=1:
    #        f.write(data_all[i])

    #f.close()



##Find the number of NS/BH collisions in the models
##Startype=13 or 14
def get_NS_collision(pathlist, start, end, startype):
    sourcedir=np.genfromtxt(pathlist, dtype=str)
    filepaths=sourcedir[:,0]; status=sourcedir[:,1]

    #model=[]; model_status=[]; mm=[]; mcom=[]; ktypem=[]; kcom=[]; timem=[]; idm=[]; rm=[]; colltype=[]
    fcoll=open('/projects/b1095/syr904/projects/PULSAR2/newruns/tidal_capture/BH_coll_all.dat', 'a+')
    fcoll.write('#1.Model 2.Time(Myr) 3.IDcoll 4.Radius(pc) 5.Mcoll 6.M0 7.M1 8.M2 9.M3 10.kcoll 11.k0 12.k1 13.k2 14.k3 15.model_status 16.COLLTYPE\n')
    for i in range(len(filepaths)):
        filestr=filepaths[i]+'initial'

        t_conv=dyn.conv('t', filestr+'.conv.sh')
        l_conv=dyn.conv('l', filestr+'.conv.sh')

        collfile=filestr+'.collision.log'
        collfile2=filestr+'2.collision.log'
        colldata=scripts1.readcollfile(collfile)
        if os.path.isfile(collfile2) and os.path.getsize(collfile2) > 0:
            colldata2=scripts1.readcollfile(collfile2)
            colldata=colldata+colldata2

        for j in range(len(colldata)):
            line=colldata[j].split()
            if line[1]=='single-single':  ##Single-single star collision
                colltype='SS'
                if int(line[11])==startype or int(line[12])==startype:
                    model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                    mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=-100; m3=-100
                    ktypem=int(line[10]); ktype0=int(line[11]); ktype1=int(line[12]); ktype2=-100; ktype3=-100
                    idm=int(line[3]); rm=float(line[9])*l_conv

                    fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))


            if line[1]=='binary-single':   ##Binary-single collision
                colltype='BS'
                if int(line[2])==2:
                    if int(line[11])==startype or int(line[12])==startype:
                        model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                        mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=-100; m3=-100
                        ktypem=int(line[10]); ktype0=int(line[11]); ktype1=int(line[12]); ktype2=-100; ktype3=-100
                        idm=int(line[3]); rm=float(line[9])*l_conv

                        fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))

                if int(line[2])==3:
                    if int(line[13])==startype or int(line[14])==startype or int(line[15])==startype:
                        model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                        mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=float(line[10]); m3=-100
                        ktypem=int(line[12]); ktype0=int(line[13]); ktype1=int(line[14]); ktype2=int(line[15]); ktype3=-100
                        idm=int(line[3]); rm=float(line[11])*l_conv

                        fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))


            if line[1]=='binary-binary':   ##Binary-binary collision
                colltype='BB'
                if int(line[2])==2:
                    if int(line[11])==startype or int(line[12])==startype:
                        model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                        mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=-100; m3=-100
                        ktypem=int(line[10]); ktype0=int(line[11]); ktype1=int(line[12]); ktype2=-100; ktype3=-100
                        idm=int(line[3]); rm=float(line[9])*l_conv

                        fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))

                if int(line[2])==3:
                    if int(line[13])==startype or int(line[14])==startype or int(line[15])==startype:
                        model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                        mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=float(line[10]); m3=-100
                        ktypem=int(line[12]); ktype0=int(line[13]); ktype1=int(line[14]); ktype2=int(line[15]); ktype3=-100
                        idm=int(line[3]); rm=float(line[11])*l_conv

                        fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))

                if int(line[2])==4:
                    if int(line[15])==startype or int(line[16])==startype or int(line[17])==startype or int(line[18])==startype:
                        model=i; model_status=int(status[i]); timem=t_conv*float(line[0])
                        mm=float(line[4]); m0=float(line[6]); m1=float(line[8]); m2=float(line[10]); m3=float(line[12])
                        ktypem=int(line[14]); ktype0=int(line[15]); ktype1=int(line[16]); ktype2=int(line[17]); ktype3=int(line[18])
                        idm=int(line[3]); rm=float(line[13])*l_conv

                        fcoll.write('%d %f %d %f %f %f %f %f %f %d %d %d %d %d %d %s\n'%(model, timem, idm, rm, mm, m0, m1, m2, m3, ktypem, ktype0, ktype1, ktype2, ktype3, model_status, colltype))


        print(i)

    fcoll.close()



##Total numbers of different collision systems
def get_num_collision(nscollfile, typeinput):
    data=np.genfromtxt(nscollfile, dtype=None)
    
    count_ms=0; count_giant=0; count_wd=0; count_nsbh=0 #; count_bh=0
    ntot=0
    for i in range(len(data)):
        if data[i][14]==1: ntot+=1
        if data[i][14]==1 and data[i][-1].decode("utf-8")==typeinput:
            klist=[data[i][10], data[i][11], data[i][12], data[i][13]]
            knum=Counter(klist)
            for j in range(15):
                if j<=1:
                    if knum[j]>=1:
                        count_ms+=1
                        break

                elif 2<=j<=9:
                   if knum[j]>=1:
                        count_giant+=1
                        break

                elif 10<=j<=12:
                    if knum[j]>=1:
                        count_wd+=1
                        break

                else:
                    if knum[j]>=1:
                        count_nsbh+=1
                        break

    print(count_ms, count_giant, count_wd, count_nsbh)
    print(ntot)



def get_NS_binint(pathlist, therv):
    sourcedir=np.genfromtxt(pathlist, dtype=str)
    #filepaths=sourcedir[:,0]; status=sourcedir[:,1]
    filepaths=['/projects/b1095/syr904/cmc/extreme_model/N8e5fbh100rv0.5_NSkick20_BHkick_300_IMF20/']; status=[1]

    id0=[]; id1=[]; m0=[]; m1=[]; k0=[]; k1=[]; a=[]; e=[]; time=[]; model=[]
    count_allbinint=[[],[],[],[]]; count_alldns=[[],[],[],[]]; count_allmerge=[[],[],[],[]]
    sma=[[], [], [], []]; m0_sma=[[],[],[],[]]; m1_sma=[[],[],[],[]]


    limit_low=[0, 2, 10, 13]; limit_high=[1, 9, 12, 14]
    for i in range(len(filepaths)):
        count_ns=[0, 0, 0, 0]; count_dns=[0, 0, 0, 0]; count_dns_merge=[0, 0, 0, 0]
        #n_ini, metal, r_g, r_v = uc.find_init_conditions(filepaths[i])
        r_v=0.5

        filestr=filepaths[i]+'initial'
        t_conv=dyn.conv('t', filestr+'.conv.sh')

        binintfile=filestr+'.binint.log'
        binintfile2=filestr+'2.binint.log'

        if int(status[i])==1 and r_v==therv:
            if os.path.isfile(binintfile2) and os.path.getsize(binintfile2) > 0:
                binint=scripts3.read_binint(binintfile2)
                for j in range(len(binint)):
                    bininput=binint[j]['input']
                    binoutput=binint[j]['output']
                    for k in range(len(bininput)):
                        if int(bininput[k]['no'])==2: 
                            for x in range(4):
                                if (int(bininput[k]['startype'][1])==13 and limit_low[x]<=int(bininput[k]['startype'][0])<=limit_high[x]) or (int(bininput[k]['startype'][0])==13 and limit_low[x]<=int(bininput[k]['startype'][1])<=limit_high[x]):
                                    count_ns[x]+=1
                                    #print bininput[k]['a']
                                    sma[x].append(float(bininput[k]['a']))
                                    m0_sma[x].append(float(bininput[k]['m'][0])); m1_sma[x].append(float(bininput[k]['m'][1]))
                                    for l in range(len(binoutput)):
                                        if int(binoutput[l]['no'])==2:
                                            if binoutput[l]['ids'][0].find(':')==-1 and binoutput[l]['ids'][1].find(':')==-1:
                                                if int(binoutput[l]['startype'][0])==13 and int(binoutput[l]['startype'][1])==13:
                                                    count_dns[x]+=1
                                                    time.append(float(binint[j]['type']['time'])*t_conv)
                                                    id0.append(int(binoutput[l]['ids'][0])); id1.append(int(binoutput[l]['ids'][1]))
                                                    m0.append(float(binoutput[l]['m'][0])); m1.append(float(binoutput[l]['m'][1]))
                                                    k0.append(int(binoutput[l]['startype'][0])); k1.append(int(binoutput[l]['startype'][1]))
                                                    a.append(float(binoutput[l]['a'])); e.append(float(binoutput[l]['e']))
                                                    model.append(i)
                                                    t_inspiral=gwcalc.t_inspiral_2(float(binoutput[l]['a']), float(binoutput[l]['e']), float(binoutput[l]['m'][0]), float(binoutput[l]['m'][1]), 0, 0, 0, 1100)/10**6 ##in Myr
                                                    if t_inspiral+float(binint[j]['type']['time'])*t_conv<14000.0:
                                                        count_dns_merge[x]+=1


            binint=scripts3.read_binint(binintfile)
            for j in range(len(binint)):
                bininput=binint[j]['input']
                binoutput=binint[j]['output']
                for k in range(len(bininput)):
                    if int(bininput[k]['no'])==2:
                        for x in range(4):
                            if (int(bininput[k]['startype'][1])==13 and limit_low[x]<=int(bininput[k]['startype'][0])<=limit_high[x]) or (int(bininput[k]['startype'][0])==13 and limit_low[x]<=int(bininput[k]['startype'][1])<=limit_high[x]):
                                count_ns[x]+=1
                                #print bininput[k]['a']
                                sma[x].append(float(bininput[k]['a']))
                                m0_sma[x].append(float(bininput[k]['m'][0])); m1_sma[x].append(float(bininput[k]['m'][1]))
                                for l in range(len(binoutput)):
                                    if int(binoutput[l]['no'])==2:
                                        if binoutput[l]['ids'][0].find(':')==-1 and binoutput[l]['ids'][1].find(':')==-1:
                                            if int(binoutput[l]['startype'][0])==13 and int(binoutput[l]['startype'][1])==13:
                                                count_dns[x]+=1
                                                time.append(float(binint[j]['type']['time'])*t_conv)
                                                id0.append(int(binoutput[l]['ids'][0])); id1.append(int(binoutput[l]['ids'][1]))
                                                m0.append(float(binoutput[l]['m'][0])); m1.append(float(binoutput[l]['m'][1]) )
                                                k0.append(int(binoutput[l]['startype'][0])); k1.append(int(binoutput[l]['startype'][1]))
                                                a.append(float(binoutput[l]['a'][0])); e.append(float(binoutput[l]['e'][0]))
                                                model.append(i)
                                                t_inspiral=lisa.inspiral_time_peters(float(binoutput[l]['a'][0]), float(binoutput[l]['e'][0]), float(binoutput[l]['m'][0]), float(binoutput[l]['m'][1]))*10**3 ##in Myr
                                                if t_inspiral+float(binint[j]['type']['time'])*t_conv<14000.0:
                                                    count_dns_merge[x]+=1
                                                    


            for y in range(4):
                count_allbinint[y].append(count_ns[y])
                count_alldns[y].append(count_dns[y])
                count_allmerge[y].append(count_dns_merge[y])


        print(i)

    print(np.sum(count_allbinint[0]), np.sum(count_alldns[0]), np.sum(count_allmerge[0]))
    print(np.sum(count_allbinint[1]), np.sum(count_alldns[1]), np.sum(count_allmerge[1]))
    print(np.sum(count_allbinint[2]), np.sum(count_alldns[2]), np.sum(count_allmerge[2]))

    return sma, m0_sma, m1_sma



            


