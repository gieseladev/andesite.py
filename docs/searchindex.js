Search.setIndex({docnames:["index","intro","quickstart","reference/clients","reference/event_target","reference/index","reference/models","reference/transform"],envversion:{"sphinx.domains.c":1,"sphinx.domains.changeset":1,"sphinx.domains.cpp":1,"sphinx.domains.javascript":1,"sphinx.domains.math":2,"sphinx.domains.python":1,"sphinx.domains.rst":1,"sphinx.domains.std":1,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":1,"sphinx.ext.viewcode":1,sphinx:55},filenames:["index.rst","intro.rst","quickstart.rst","reference/clients.rst","reference/event_target.rst","reference/index.rst","reference/models.rst","reference/transform.rst"],objects:{"andesite.AndesiteHTTP":{aiohttp_session:[3,1,1,""],close:[3,2,1,""],decode_track:[3,2,1,""],decode_tracks:[3,2,1,""],get_stats:[3,2,1,""],load_tracks:[3,2,1,""],request:[3,2,1,""]},"andesite.AndesiteWebSocket":{connect:[3,2,1,""],connected:[3,1,1,""],destroy:[3,2,1,""],disconnect:[3,2,1,""],filters:[3,2,1,""],get_player:[3,2,1,""],get_stats:[3,2,1,""],max_connect_attempts:[3,1,1,""],mixer:[3,2,1,""],pause:[3,2,1,""],ping:[3,2,1,""],play:[3,2,1,""],seek:[3,2,1,""],send:[3,2,1,""],send_operation:[3,2,1,""],stop:[3,2,1,""],update:[3,2,1,""],voice_server_update:[3,2,1,""],volume:[3,2,1,""],web_socket_client:[3,1,1,""]},"andesite.event_target":{Event:[4,0,1,""],EventErrorEvent:[4,0,1,""],EventListener:[4,0,1,""],EventTarget:[4,0,1,""],OneTimeEventListener:[4,0,1,""]},"andesite.event_target.Event":{name:[4,1,1,""]},"andesite.event_target.EventErrorEvent":{exception:[4,1,1,""],handler:[4,1,1,""],original_event:[4,1,1,""]},"andesite.event_target.EventListener":{handler:[4,1,1,""]},"andesite.event_target.EventTarget":{add_listener:[4,2,1,""],dispatch:[4,2,1,""],on_event_error:[4,2,1,""],remove_listener:[4,2,1,""],wait_for:[4,2,1,""]},"andesite.event_target.OneTimeEventListener":{condition:[4,1,1,""],future:[4,1,1,""]},"andesite.models":{debug:[6,3,0,"-"],filters:[6,3,0,"-"],operations:[6,3,0,"-"],player:[6,3,0,"-"],track:[6,3,0,"-"]},"andesite.models.debug":{Error:[6,0,1,""],StackFrame:[6,0,1,""]},"andesite.models.debug.Error":{cause:[6,1,1,""],class_name:[6,1,1,""],message:[6,1,1,""],stack:[6,1,1,""],suppressed:[6,1,1,""]},"andesite.models.debug.StackFrame":{class_loader:[6,1,1,""],class_name:[6,1,1,""],file_name:[6,1,1,""],line_number:[6,1,1,""],method_name:[6,1,1,""],module_name:[6,1,1,""],module_version:[6,1,1,""],pretty:[6,1,1,""]},"andesite.models.filters":{Equalizer:[6,0,1,""],EqualizerBand:[6,0,1,""],Karaoke:[6,0,1,""],Timescale:[6,0,1,""],Tremolo:[6,0,1,""],Vibrato:[6,0,1,""],VolumeFilter:[6,0,1,""]},"andesite.models.filters.Equalizer":{bands:[6,1,1,""],get_band:[6,2,1,""],get_band_gain:[6,2,1,""],set_band_gain:[6,2,1,""]},"andesite.models.filters.EqualizerBand":{band:[6,1,1,""],gain:[6,1,1,""],set_band:[6,2,1,""],set_gain:[6,2,1,""]},"andesite.models.filters.Karaoke":{filter_band:[6,1,1,""],filter_width:[6,1,1,""],level:[6,1,1,""],mono_level:[6,1,1,""]},"andesite.models.filters.Timescale":{pitch:[6,1,1,""],rate:[6,1,1,""],set_pitch:[6,2,1,""],set_rate:[6,2,1,""],set_speed:[6,2,1,""],speed:[6,1,1,""]},"andesite.models.filters.Tremolo":{depth:[6,1,1,""],frequency:[6,1,1,""],set_depth:[6,2,1,""],set_frequency:[6,2,1,""]},"andesite.models.filters.Vibrato":{depth:[6,1,1,""],frequency:[6,1,1,""],set_depth:[6,2,1,""],set_frequency:[6,2,1,""]},"andesite.models.filters.VolumeFilter":{volume:[6,1,1,""]},"andesite.models.operations":{FilterUpdate:[6,0,1,""],MixerUpdate:[6,0,1,""],Operation:[6,0,1,""],Pause:[6,0,1,""],Play:[6,0,1,""],Seek:[6,0,1,""],Update:[6,0,1,""],VoiceServerUpdate:[6,0,1,""],Volume:[6,0,1,""]},"andesite.models.operations.FilterUpdate":{equalizer:[6,1,1,""],karaoke:[6,1,1,""],timescale:[6,1,1,""],tremolo:[6,1,1,""],vibrato:[6,1,1,""],volume:[6,1,1,""]},"andesite.models.operations.MixerUpdate":{enable:[6,1,1,""],players:[6,1,1,""]},"andesite.models.operations.Pause":{pause:[6,1,1,""]},"andesite.models.operations.Play":{end:[6,1,1,""],no_replace:[6,1,1,""],pause:[6,1,1,""],start:[6,1,1,""],track:[6,1,1,""],volume:[6,1,1,""]},"andesite.models.operations.Seek":{position:[6,1,1,""]},"andesite.models.operations.Update":{filters:[6,1,1,""],pause:[6,1,1,""],position:[6,1,1,""],volume:[6,1,1,""]},"andesite.models.operations.VoiceServerUpdate":{event:[6,1,1,""],session_id:[6,1,1,""]},"andesite.models.operations.Volume":{volume:[6,1,1,""]},"andesite.models.player":{BasePlayer:[6,0,1,""],MixerPlayer:[6,0,1,""],Player:[6,0,1,""]},"andesite.models.player.BasePlayer":{filters:[6,1,1,""],live_position:[6,1,1,""],paused:[6,1,1,""],position:[6,1,1,""],time:[6,1,1,""],volume:[6,1,1,""]},"andesite.models.player.Player":{mixer:[6,1,1,""],mixer_enabled:[6,1,1,""]},"andesite.models.track":{LoadType:[6,0,1,""],LoadedTrack:[6,0,1,""],PlaylistInfo:[6,0,1,""],TrackInfo:[6,0,1,""],TrackMetadata:[6,0,1,""]},"andesite.models.track.LoadType":{LOAD_FAILED:[6,1,1,""],NO_MATCHES:[6,1,1,""],PLAYLIST_LOADED:[6,1,1,""],SEARCH_RESULT:[6,1,1,""],TRACK_LOADED:[6,1,1,""]},"andesite.models.track.LoadedTrack":{cause:[6,1,1,""],load_type:[6,1,1,""],playlist_info:[6,1,1,""],severity:[6,1,1,""],tracks:[6,1,1,""]},"andesite.models.track.PlaylistInfo":{name:[6,1,1,""],selected_track:[6,1,1,""]},"andesite.models.track.TrackInfo":{info:[6,1,1,""],track:[6,1,1,""]},"andesite.models.track.TrackMetadata":{author:[6,1,1,""],class_name:[6,1,1,""],identifier:[6,1,1,""],is_seekable:[6,1,1,""],is_stream:[6,1,1,""],length:[6,1,1,""],position:[6,1,1,""],title:[6,1,1,""],uri:[6,1,1,""]},"andesite.transform":{build_from_raw:[7,4,1,""],convert_to_raw:[7,4,1,""],from_milli:[7,4,1,""],map_build_all_values_from_raw:[7,4,1,""],map_build_values_from_raw:[7,4,1,""],map_convert_value:[7,4,1,""],map_convert_values:[7,4,1,""],map_convert_values_all:[7,4,1,""],map_convert_values_from_milli:[7,4,1,""],map_convert_values_to_milli:[7,4,1,""],map_filter_none:[7,4,1,""],seq_build_all_items_from_raw:[7,4,1,""],to_milli:[7,4,1,""]},andesite:{AndesiteHTTP:[3,0,1,""],AndesiteWebSocket:[3,0,1,""],event_target:[4,3,0,"-"],transform:[7,3,0,"-"]}},objnames:{"0":["py","class","Python class"],"1":["py","attribute","Python attribute"],"2":["py","method","Python method"],"3":["py","module","Python module"],"4":["py","function","Python function"]},objtypes:{"0":"py:class","1":"py:attribute","2":"py:method","3":"py:module","4":"py:function"},terms:{"abstract":6,"class":[3,4,6],"default":[3,6],"export":[3,6],"final":4,"float":[3,4,6,7],"function":[3,7],"import":6,"int":[3,6,7],"new":6,"return":[3,4,6,7],"true":[3,4,6],"while":[4,6],For:7,Its:7,One:4,The:[3,4,6,7],These:7,Uses:7,Using:3,__transform_input__:7,__transform_output__:7,abc:6,abil:3,abort:[3,4,7],abstracteventloop:[3,4],accept:4,accur:3,action:[4,7],actual:3,add:4,add_listen:4,added:[3,4],adding:4,addit:3,after:[3,7],aggreg:4,aiohttp:3,aiohttp_sess:3,all:[3,4,6,7],along:3,alreadi:[3,4,6],also:[3,6,7],amount:[3,4],andesit:[3,6,7],andesitehttp:3,andesitewebsocket:[3,6],ani:[3,4,6,7],anyth:[3,7],anywai:3,appear:6,appli:7,argument:[3,7],arrai:6,asdict:7,assign:7,asynchron:[3,4],attempt:3,attribut:[3,6],audio:6,author:6,automat:6,await:4,band:6,base64:[3,6],base:[3,4,6,7],baseplay:6,becaus:3,been:4,befor:[3,4,7],behav:7,below:7,bool:[3,4,6],build:7,build_from_raw:7,built:7,call:[3,4,6,7],callabl:[4,7],callback:[4,7],calle:4,can:[3,4,6,7],caus:[4,6],check:[3,4,6],class_load:6,class_nam:6,classload:6,classmethod:7,client:[0,5,6],clientsess:3,close:3,cls:7,comfort:6,command:[3,6],commun:4,complet:7,condit:4,configur:[3,6],connect:3,constructor:7,contain:4,content:0,control:[3,6],convers:[3,7],convert:[3,7],convert_to_raw:7,copi:7,coroutin:[3,4],cover:3,creat:6,current:[3,6],data:[3,6,7],dataclass:7,datetim:6,debug:5,decod:3,decode_track:3,defin:3,depth:6,destroi:3,dict:[3,6,7],differ:7,directli:3,disconnect:3,discord:[3,6],dispatch:[3,4],divid:7,doe:[3,6,7],doesn:[3,6,7],don:[3,4,6],dromedarycas:7,due:3,durat:6,dure:4,dynam:[3,4],each:[3,6,7],effici:3,either:3,enabl:[3,6],encod:[3,6],end:[3,6],endpoint:3,entiti:6,equal:[3,6],equalizerband:6,error:[4,6],event:[0,3,5,6],eventerrorev:4,eventfilt:4,eventhandl:4,eventlisten:4,eventtarget:4,except:4,execut:4,exist:[6,7],fail:3,fals:[3,4,6],field:3,file:6,file_nam:6,filter:[3,5,7],filter_band:6,filter_upd:3,filter_width:6,filtermap:6,filterupd:[3,6],first:[3,4],forev:4,found:6,frame:6,frequenc:6,from:[3,6,7],from_milli:7,func:7,futur:4,gain:6,get:[3,6],get_band:6,get_band_gain:6,get_play:3,get_stat:3,give:3,given:[3,4],good:3,guild:[3,6],guild_id:3,handler:[3,4],happen:6,has:6,have:[3,4],honest:7,how:3,howev:[3,7],http:5,http_client:3,idempot:3,identifi:[3,6],ignor:[3,6,7],includ:3,index:[0,6,7],inf:6,info:6,inform:4,instal:0,instanc:[3,4,7],instead:[3,4],interact:[3,6],interpol:6,introduct:0,invalid:[3,6],is_seek:6,is_stream:6,isn:3,item:7,iter:3,its:7,itself:4,json:3,just:7,karaok:[3,6],kei:7,key_func:7,key_typ:7,keyword:[3,7],kwarg:[3,4],lavaplay:[3,6],length:6,less:3,let:7,level:6,librari:0,like:7,limit:3,line:6,line_numb:6,list:[3,6,7],listen:4,live_posit:6,livestream:6,load:[3,6],load_fail:6,load_track:3,load_typ:6,loadedtrack:[3,6],loadtyp:6,loop:[3,4],lot:6,made:3,mai:[3,7],mainli:3,make:[3,4,6],mani:3,manipul:7,manual:3,map:[3,6,7],map_build_all_values_from_raw:7,map_build_values_from_raw:7,map_convert_valu:7,map_convert_values_al:7,map_convert_values_from_milli:7,map_convert_values_to_milli:7,map_filter_non:7,mapfunct:7,match:4,max:3,max_attempt:3,max_connect_attempt:3,meet:4,member:7,messag:[3,6],meta:4,metadata:6,method:[3,4,6,7],method_nam:6,milli:7,mixer:[3,6],mixer_en:6,mixermap:6,mixerplay:6,mixerplayerupdatemap:6,mixerupd:6,model:[0,5,7],modifi:7,modul:[0,6],module_nam:6,module_vers:6,mono_level:6,more:6,multipl:3,multipli:7,music:6,must:3,mutabl:7,mutablemap:7,mutablesequ:7,mutat:[3,7],name:[3,4,6],namespac:[3,6],need:[3,4],next:4,no_match:6,no_replac:[3,6],node:6,none:[3,4,6,7],note:3,noth:6,number:[6,7],obj:7,object:[4,7],occur:4,old:7,on_:4,on_event_error:4,onc:[3,4],one:4,onetimeeventlisten:4,onli:4,oper:[3,5],option:[3,4,6,7],order:3,origin:4,original_ev:4,other:[3,7],otherwis:[4,6,7],out:4,outlin:7,overhead:3,page:0,paramet:[3,4,6,7],pars:7,pass:[3,4,6,7],path:3,paus:[3,6],payload:[3,6],perform:[3,6,7],persist:4,ping:3,pitch:6,plai:[3,6],player:[3,5],playlist:6,playlist_info:6,playlist_load:6,playlistinfo:6,pleas:3,posit:[3,6],presenc:3,present:[3,6],pretti:6,previou:7,previous:4,print:6,printstacktrac:6,propag:4,properti:3,provid:[3,4,6,7],python:[6,7],queue:3,quick:0,rais:[3,4,6],rate:6,raw:7,raw_data:7,realli:7,reason:3,receiv:[3,4],refer:0,regardless:3,rel:3,relat:6,remov:[4,7],remove_listen:4,replac:7,represent:7,request:3,resid:6,respons:[3,6],result:[4,7],retriev:[3,4],rout:3,run:7,said:4,same:[4,7],search:0,search_result:6,second:[3,4,6],see:6,seek:[3,6],select:6,selected_track:6,self:[3,4],send:3,send_oper:[3,6],sent:[3,6,7],seq_build_all_items_from_raw:7,sequenc:7,server:[3,6],session:[3,6],session_id:[3,6],set:[3,4,6],set_band:6,set_band_gain:6,set_depth:6,set_frequ:6,set_gain:6,set_pitch:6,set_rat:6,set_spe:6,setter:6,sever:6,should:[3,6,7],similar:[4,7],similarli:7,slash:3,snake_cas:7,socket:5,some:4,someth:7,soon:3,sourc:[3,4,6,7],special:[4,6],specifi:[3,4,6,7],speed:6,stack:6,stackfram:6,stacktrac:6,start:[0,3,6],stat:3,stop:3,store:6,str:[3,4,6,7],string:3,successfulli:[3,4],support:6,suppress:6,sure:4,take:4,target:[0,3,5,7],than:[3,7],thei:[3,6],them:[6,7],thi:[3,4,6,7],those:4,throwabl:6,time:[4,6],timeout:4,timescal:[3,6],timestamp:[3,6],titl:6,to_milli:7,todo:[1,2],took:3,track:[3,5],track_load:6,trackinfo:[3,6],trackmetadata:6,transform:[0,5],tremolo:[3,6],tupl:7,type:[3,4,6,7],underli:3,union:[3,4],unit:7,unlimit:3,unpaus:3,updat:[3,6],upper:3,uri:[3,6],url:3,usabl:3,use:3,used:[3,4,6,7],user:6,using:7,usual:7,utc:6,util:7,valid:3,valu:[4,6,7],valueerror:[3,6],variou:4,version:6,vibrato:[3,6],voic:[3,6],voice_server_upd:3,voiceserverupd:[3,6],volum:[3,6],volumefilt:[3,6],wait:4,wait_for:4,want:6,web:5,web_socket_cli:3,websocket:3,websocketclientprotocol:3,when:[3,4],whenev:4,whether:[3,4,6],which:[3,4,6,7],whose:7,wish:3,without:7,work:7,would:6,written:3,ws_connect:3,ws_send:3,yield:4,you:[3,4,6,7]},titles:["Welcome to andesite.py\u2019s documentation!","Introduction","Quick-start","Clients","Event Target","Reference","Models","Transform"],titleterms:{andesit:0,client:3,debug:6,document:0,event:4,filter:6,http:3,indic:0,instal:1,introduct:1,model:6,oper:6,player:6,quick:2,refer:5,socket:3,start:2,tabl:0,target:4,track:6,transform:7,web:3,welcom:0}})