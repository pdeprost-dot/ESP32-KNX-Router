#include <Arduino.h>
#include <ESPBase.h>
#include <Preferences.h>
#include <WiFi.h>
#include <knx.h>
#include <knx/bau091A.h>
#include "router_config.h"

namespace {
constexpr char kFirmwareVersion[]="0.2.0", kNvs[]="knxrouter";
constexpr uint16_t kConfigVersion=1, kDefaultPort=3671;
constexpr uint32_t kDefaultMulticast=0xE000170CUL;
struct RouterConfig { uint16_t version=kConfigVersion; bool paSet=false; uint16_t pa=0; uint32_t multicast=kDefaultMulticast; uint16_t port=kDefaultPort; uint32_t timeoutMs=15000, probeMs=3000; };
enum class Diag:uint8_t { Idle,Running,ResetReceived,Absent,ProtocolError,BusMonitor };

ESPBase espBase(ROUTER_NAME,kFirmwareVersion); Preferences prefs; RouterConfig config;
HardwareSerial knxSerial(2); Esp32Platform knxPlatform(&knxSerial); Bau091A knxBau(knxPlatform); KnxFacade<Esp32Platform,Bau091A> knx(knxBau);
Diag diag=Diag::Idle; uint32_t diagStart=0,lastProbe=0,attempts=0,resetInd=0,stateInd=0,tpFrames=0,overflows=0,lastByteUs=0; uint8_t frame[64]{}; size_t frameLen=0; bool configLoaded=false; char lastDiagnostic[96]="Diagnostic non lance",lastError[96]="Aucune";

bool elapsed(uint32_t now,uint32_t since,uint32_t duration){return uint32_t(now-since)>=duration;}
void setText(char* dst,size_t cap,const char* value){strlcpy(dst,value?value:"",cap);}
const char* diagText(){switch(diag){case Diag::Idle:return "Non lance";case Diag::Running:return "En cours";case Diag::ResetReceived:return "Reponse recue";case Diag::Absent:return "NanoBCU non detecte";case Diag::ProtocolError:return "Erreur de protocole";case Diag::BusMonitor:return "Bus monitor passif";}return "Inconnu";}
void formatPa(uint16_t a,char* out,size_t cap){snprintf(out,cap,"%u.%u.%u",(a>>12)&15,(a>>8)&15,a&255);}
bool parsePa(const char* s,bool& configured,uint16_t& out){configured=false;out=0;if(!s||!*s)return true;unsigned a,l,d;char x;if(sscanf(s,"%u.%u.%u%c",&a,&l,&d,&x)!=3||a>15||l>15||d>255)return false;configured=true;out=(a<<12)|(l<<8)|d;return true;}
void formatIp(uint32_t a,char* out,size_t cap){snprintf(out,cap,"%u.%u.%u.%u",(a>>24)&255,(a>>16)&255,(a>>8)&255,a&255);}
bool parseIp(const char* s,uint32_t& out){unsigned a,b,c,d;char x;if(!s||sscanf(s,"%u.%u.%u.%u%c",&a,&b,&c,&d,&x)!=4||a<224||a>239||b>255||c>255||d>255)return false;out=(a<<24)|(b<<16)|(c<<8)|d;return true;}
bool parseUInt(const char* s,uint32_t lo,uint32_t hi,uint32_t& out){if(!s||!*s)return false;char* e=nullptr;unsigned long v=strtoul(s,&e,10);if(!e||*e||v<lo||v>hi)return false;out=v;return true;}
bool valid(const RouterConfig& c){uint8_t first=c.multicast>>24;return c.version==kConfigVersion&&first>=224&&first<=239&&c.port&&c.timeoutMs>=3000&&c.timeoutMs<=60000&&c.probeMs>=500&&c.probeMs<=10000&&c.probeMs<c.timeoutMs;}
bool loadConfig(){if(!prefs.begin(kNvs,true))return false;RouterConfig candidate;size_t n=prefs.getBytesLength("config")==sizeof(candidate)?prefs.getBytes("config",&candidate,sizeof(candidate)):0;prefs.end();if(n!=sizeof(candidate)||!valid(candidate))return false;config=candidate;return true;}
bool saveConfig(const RouterConfig& c){if(!valid(c)||!prefs.begin(kNvs,false))return false;size_t n=prefs.putBytes("config",&c,sizeof(c));prefs.end();return n==sizeof(c);}

void startDiagnostic(){while(knxSerial.available())knxSerial.read();diag=Diag::Running;diagStart=millis();lastProbe=diagStart-config.probeMs;attempts=0;frameLen=0;setText(lastDiagnostic,sizeof(lastDiagnostic),"Diagnostic NCN5130 en cours");setText(lastError,sizeof(lastError),"Aucune");Serial.println(F("[NANOBCU] Diagnostic local demarre"));}
void finishFrame(){if(diag!=Diag::BusMonitor||!frameLen)return;++tpFrames;Serial.printf("[TP-RX #%lu] %u octets:",tpFrames,unsigned(frameLen));for(size_t i=0;i<frameLen;++i)Serial.printf(" %02X",frame[i]);Serial.println();frameLen=0;}
void serviceDiagnostic(){
 if(diag==Diag::BusMonitor&&frameLen&&elapsed(micros(),lastByteUs,NANOBCU_FRAME_GAP_US))finishFrame();
 while(knxSerial.available()){uint8_t v=knxSerial.read();if(diag==Diag::Running&&v==0x03){++resetInd;diag=Diag::ResetReceived;setText(lastDiagnostic,sizeof(lastDiagnostic),"U_Reset.ind recu; lecture etat NCN5130");knxSerial.write(0x02);knxSerial.flush();}
 else if(diag==Diag::ResetReceived&&(v&7)==7){++stateInd;diag=Diag::BusMonitor;setText(lastDiagnostic,sizeof(lastDiagnostic),"NCN5130 detecte; bus monitor passif actif");knxSerial.write(0x05);knxSerial.flush();Serial.printf("[NANOBCU] U_State.ind=0x%02X; bus monitor passif\n",v);}
 else if(diag==Diag::BusMonitor){lastByteUs=micros();if(frameLen<sizeof(frame))frame[frameLen++]=v;else{++overflows;frameLen=0;setText(lastError,sizeof(lastError),"Trame UART depasse 64 octets");}}
 else if(diag==Diag::ResetReceived){diag=Diag::ProtocolError;snprintf(lastError,sizeof(lastError),"Reponse etat inattendue 0x%02X",v);}}
 uint32_t now=millis();if(diag==Diag::Running&&elapsed(now,diagStart,config.timeoutMs)){diag=Diag::Absent;setText(lastDiagnostic,sizeof(lastDiagnostic),"NanoBCU non detecte");Serial.println(F("[NANOBCU] NanoBCU non detecte (normal si debranche)"));}
 else if(diag==Diag::Running&&elapsed(now,lastProbe,config.probeMs)){lastProbe=now;++attempts;knxSerial.write(0x01);knxSerial.flush();}
}

void metric(WebResponse& r,const char* label,const char* value){r.write("<div><span class='muted'>");r.write(label);r.write("</span><strong>");r.write(value);r.write("</strong></div>");}
void statePage(WebResponse& r,void*){char v[96];r.beginPage("KNX - Etat");r.write("<div class='grid'><section class='card'><h2>Routeur KNX</h2><div class='metrics'>");metric(r,"Firmware",espBase.firmwareVersion());metric(r,"Device ID",espBase.deviceId());metric(r,"Hostname",espBase.hostname());snprintf(v,sizeof(v),"%lu s",millis()/1000UL);metric(r,"Uptime",v);r.write("</div></section><section class='card'><h2>Reseau</h2><div class='metrics'>");metric(r,"Wi-Fi",WiFi.status()==WL_CONNECTED?"Connecte":"Deconnecte");metric(r,"Adresse IP",WiFi.localIP().toString().c_str());snprintf(v,sizeof(v),"%ld dBm",long(WiFi.status()==WL_CONNECTED?WiFi.RSSI():0));metric(r,"RSSI",v);r.write("</div></section><section class='card'><h2>NanoBCU NCN5130</h2><div class='metrics'>");metric(r,"Etat",diagText());metric(r,"UART","UART2 RX GPIO16 / TX GPIO17 - 19200 8E1");metric(r,"Mode demande","Diagnostic local puis bus monitor");metric(r,"Mode actif",diag==Diag::BusMonitor?"Bus monitor passif":"Diagnostic local");snprintf(v,sizeof(v),"%lu",attempts);metric(r,"Tentatives",v);snprintf(v,sizeof(v),"%lu",tpFrames);metric(r,"Trames TP recues",v);metric(r,"Dernier diagnostic",lastDiagnostic);metric(r,"Derniere erreur",lastError);r.write("</div><form method='post' action='/knx-diagnostic'><button type='submit'>Relancer le diagnostic local</button></form></section><section class='card'><h2>Routage</h2><div class='metrics'>");metric(r,"Verrou compile",ROUTING_ARMED?"ARME":"DESACTIVE");metric(r,"Pile KNXnet/IP","Arretee");metric(r,"Routage TP vers IP","Inactif");metric(r,"Routage IP vers TP","Inactif");metric(r,"Tunnels","Inactifs");metric(r,"Compteurs IP","Inactifs (pile arretee)");r.write("</div></section></div>");r.endPage();}
void configPage(WebResponse& r,void*){char pa[16]="",mc[20],n[16];if(config.paSet)formatPa(config.pa,pa,sizeof(pa));formatIp(config.multicast,mc,sizeof(mc));r.beginPage("KNX - Configuration");r.write("<section class='card'><p class='muted'>ROUTING_ARMED=0 reste prioritaire. Les parametres KNXnet/IP seront appliques uniquement dans une future phase de routage.</p><form method='post' action='/knx-config-save'><label>Adresse physique prevue (vide = non configuree)<input name='physical_address' maxlength='10' placeholder='1.1.0' value='");if(pa[0])r.write(pa);r.write("'></label><label>Multicast KNXnet/IP (futur, redemarrage requis)<input name='multicast' maxlength='15' required value='");r.write(mc);snprintf(n,sizeof(n),"%u",config.port);r.write("'></label><label>Port UDP KNXnet/IP (futur, redemarrage requis)<input name='port' type='number' min='1' max='65535' required value='");r.write(n);snprintf(n,sizeof(n),"%lu",config.timeoutMs);r.write("'></label><label>Delai diagnostic, ms<input name='diag_timeout' type='number' min='3000' max='60000' required value='");r.write(n);snprintf(n,sizeof(n),"%lu",config.probeMs);r.write("'></label><label>Intervalle sondes, ms<input name='probe_interval' type='number' min='500' max='10000' required value='");r.write(n);r.write("'></label><button type='submit'>Enregistrer explicitement</button></form></section><section class='card'><h2>Parametres fixes</h2><p>UART2 RX GPIO16 / TX GPIO17, 19200 bauds, 8E1.</p><p>Filtrage : table ETS de la pile KNX uniquement; aucun filtre Web n'est implemente.</p></section>");r.endPage();}
void configPost(WebRequest& q,WebResponse& r,void*){for(const char* name:{"physical_address","multicast","port","diag_timeout","probe_interval"})if(!q.hasArg(name)){r.sendText("Parametres manquants",400);return;}RouterConfig c=config;String pa=q.arg("physical_address"),mc=q.arg("multicast"),p=q.arg("port"),t=q.arg("diag_timeout"),i=q.arg("probe_interval");uint32_t x;if(!parsePa(pa.c_str(),c.paSet,c.pa)||!parseIp(mc.c_str(),c.multicast)||!parseUInt(p.c_str(),1,65535,x)){r.sendText("Adresse physique, multicast ou port invalide",400);return;}c.port=x;if(!parseUInt(t.c_str(),3000,60000,c.timeoutMs)||!parseUInt(i.c_str(),500,10000,c.probeMs)||!valid(c)){r.sendText("Parametres de diagnostic invalides",400);return;}if(!saveConfig(c)){r.sendText("Echec enregistrement NVS",500);return;}config=c;configLoaded=true;r.sendText("Configuration enregistree. Les parametres de routage restent inactifs.");}
void diagnosticPost(WebRequest&,WebResponse& r,void*){if(diag==Diag::Running||diag==Diag::ResetReceived){r.sendText("Diagnostic deja en cours",409);return;}startDiagnostic();r.sendText("Diagnostic lance; consulter KNX - Etat",202);}

void appSetup(){static_assert(ROUTING_ARMED==0,"Cette version Web conserve le routage verrouille");Serial.begin(SERIAL_BAUD);knxSerial.begin(KNX_UART_BAUD,SERIAL_8E1,KNX_RX_PIN,KNX_TX_PIN);configLoaded=loadConfig();if(!configLoaded)setText(lastDiagnostic,sizeof(lastDiagnostic),"Configuration KNX par defaut chargee");bool ok=espBase.addPage("KNX - Etat","/knx",statePage)&&espBase.addPage("KNX - Config","/knx-config",configPage)&&espBase.addPostRoute("/knx-config-save",configPost)&&espBase.addPostRoute("/knx-diagnostic",diagnosticPost);if(!ok)setText(lastError,sizeof(lastError),"Enregistrement routes Web impossible");espBase.begin();Serial.println(F("[SECURITE] ROUTING_ARMED=0; KNXnet/IP, multicast et tunnels arretes"));startDiagnostic();}
void appLoop(){espBase.loop();serviceDiagnostic();/* knx.start() et knx.loop() volontairement absents. */}
} // namespace

void setup(){appSetup();}
void loop(){appLoop();}
