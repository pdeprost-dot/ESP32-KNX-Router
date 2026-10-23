#pragma once
#include <Arduino.h>
namespace routing_policy {
constexpr uint16_t kVersion=2; constexpr size_t kAddressCount=65536,kBitmapBytes=kAddressCount/8,kMaxImportBytes=12288;
enum class GroupMode:uint8_t{Block=0,RouteAll=1,Filter=2}; enum class IndividualMode:uint8_t{Block=0,Topology=1};
struct Direction{GroupMode groups=GroupMode::Block;IndividualMode individuals=IndividualMode::Block;bool broadcast=false;};
// One shared table intentionally serves both directions, as in schema v1.
struct Model{uint16_t version=kVersion;Direction ipToTp;Direction tpToIp;uint32_t checksum=0;uint8_t groups[kBitmapBytes]{};};
inline bool validMode(GroupMode m){return m==GroupMode::Block||m==GroupMode::RouteAll||m==GroupMode::Filter;}
inline bool validMode(IndividualMode m){return m==IndividualMode::Block||m==IndividualMode::Topology;}
inline uint32_t checksum(const Model&m){uint32_t v=2166136261UL;const uint8_t*p=reinterpret_cast<const uint8_t*>(&m);for(size_t i=0;i<offsetof(Model,checksum);++i)v=(v^p[i])*16777619UL;for(uint8_t b:m.groups)v=(v^b)*16777619UL;return v;}
inline void seal(Model&m){m.version=kVersion;m.checksum=checksum(m);} inline bool valid(const Model&m){return m.version==kVersion&&validMode(m.ipToTp.groups)&&validMode(m.tpToIp.groups)&&validMode(m.ipToTp.individuals)&&validMode(m.tpToIp.individuals)&&m.checksum==checksum(m);}
inline void clear(Model&m){memset(m.groups,0,sizeof(m.groups));} inline void set(Model&m,uint16_t a,bool on=true){uint8_t mask=uint8_t(1U<<(a&7));if(on)m.groups[a>>3]|=mask;else m.groups[a>>3]&=uint8_t(~mask);} inline bool contains(const Model&m,uint16_t a){return(m.groups[a>>3]&uint8_t(1U<<(a&7)))!=0;}
inline void setRange(Model&m,uint16_t first,uint16_t last){for(uint32_t a=first;a<=last;++a)set(m,uint16_t(a));}
inline bool groupAllowed(const Model&m,const Direction&d,uint16_t a){if(d.groups==GroupMode::RouteAll)return true;if(d.groups==GroupMode::Block)return false;return contains(m,a);}
inline bool parseGroup(const char*t,uint16_t&a){unsigned main=0,middle=0,sub=0;char tail=0;if(!t||sscanf(t,"%u/%u/%u%c",&main,&middle,&sub,&tail)!=3||main>31||middle>7||sub>255)return false;a=uint16_t((main<<11)|(middle<<8)|sub);return true;}
inline void formatGroup(uint16_t a,char*out,size_t cap){snprintf(out,cap,"%u/%u/%u",(a>>11)&31,(a>>8)&7,a&255);}
// Parse directly into the bitmap; no unbounded range list is constructed.
inline bool parseRanges(const char*text,Model&m,char*error,size_t cap){clear(m);if(!text){seal(m);return true;}size_t length=strlen(text);if(length>kMaxImportBytes){snprintf(error,cap,"Import trop volumineux (%u octets maximum)",unsigned(kMaxImportBytes));return false;}const char*cursor=text;while(*cursor==' '||*cursor=='\t')++cursor;if(!strncmp(cursor,"KXRF1:",6))cursor+=6;while(*cursor){while(*cursor==' '||*cursor=='\t'||*cursor==',')++cursor;if(!*cursor)break;const char*end=strchr(cursor,',');size_t n=end?size_t(end-cursor):strlen(cursor);while(n&&(cursor[n-1]==' '||cursor[n-1]=='\t'))--n;if(!n||n>=40){snprintf(error,cap,"Entree de filtre trop longue");return false;}char item[40];memcpy(item,cursor,n);item[n]=0;char*dash=strchr(item,'-');if(dash){*dash++=0;while(*dash==' '||*dash=='\t')++dash;char*leftEnd=item+strlen(item);while(leftEnd>item&&(leftEnd[-1]==' '||leftEnd[-1]=='\t'))*--leftEnd=0;}uint16_t first=0,last=0;if(!parseGroup(item,first)||!parseGroup(dash?dash:item,last)||first>last){snprintf(error,cap,"Entree de filtre invalide: %.32s",item);return false;}setRange(m,first,last);cursor=end?end+1:cursor+n;}seal(m);return valid(m);}
inline size_t selectedCount(const Model&m){size_t n=0;for(uint8_t b:m.groups)n+=__builtin_popcount(b);return n;}
inline const char*groupModeName(GroupMode m){return m==GroupMode::Block?"block":m==GroupMode::RouteAll?"all":"filter";} inline bool parseGroupMode(const String&t,GroupMode&m){if(t=="block")m=GroupMode::Block;else if(t=="all")m=GroupMode::RouteAll;else if(t=="filter")m=GroupMode::Filter;else return false;return true;}
}
