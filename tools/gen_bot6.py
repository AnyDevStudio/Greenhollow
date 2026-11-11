# Writes bot6.cpp: Greenhollow 2 played through by a script against the real game runtime, with two players.
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(f'{HERE}/ids6.json')); root = sys.argv[1]
defs = ''.join(f'constexpr std::size_t G_{k}={v};\n' for k, v in ids['game'].items() if k != 'from')
defs += f"constexpr std::size_t G_from={ids['game']['from']};\n"
defs += ''.join(f'constexpr std::size_t P_{k}={v};\n' for k, v in ids['player'].items())
defs += ''.join(f'constexpr std::size_t C_{k}={v};\n' for k, v in ids['copy'].items())
defs += ''.join(f"constexpr std::size_t I_{k.replace('.', '_').replace('~', '_')}={v};\n" for k, v in ids['items'].items())
defs += ''.join(f'constexpr std::size_t S_{k}={v};\n' for k, v in ids['scenes'].items())
src = r'''
#include "Scene/SceneState.hpp"
#include "Input/Buttons.hpp"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <new>
#include <string>
#include <vector>
static std::size_t allocations=0;
void* operator new(std::size_t size){++allocations; if(void* m=std::malloc(size)) return m; std::abort();}
void operator delete(void* m) noexcept{std::free(m);}
void operator delete(void* m,std::size_t) noexcept{std::free(m);}
namespace GeneratedScene {
static std::vector<std::vector<std::int32_t>> loadedCells;
static std::array<const std::int32_t*,TilemapCount> LoadCells(){
    std::array<const std::int32_t*,TilemapCount> out{};
    loadedCells.resize(TilemapCount);
    for(std::size_t i=0;i<TilemapCount;++i){
        auto& v=loadedCells[i]; v.resize(Tilemaps[i].columns*Tilemaps[i].rows);
        std::ifstream f("@ROOT@/src/GeneratedImages/tilemap-"+std::to_string(i)+".tiles",std::ios::binary);
        if(!f) std::abort();
        f.read(reinterpret_cast<char*>(v.data()),static_cast<std::streamsize>(v.size()*4));
        out[i]=v.data();
    }
    return out;
}
const std::array<const std::int32_t*,TilemapCount> TilemapCells=LoadCells();
}
@IDS@
static int failures=0;
#define CHECK(c,msg) do{ bool ok=(c); std::printf("%s  %s\n",ok?"ok  ":"FAIL",msg); if(!ok)++failures; }while(0)
using In=SceneState::PlayerInput;
static SceneState* g;
static SceneState::SaveMailbox* mail;
static std::array<std::int32_t,GeneratedVariables::SavedCount> disk{};
static bool onDisk=false;
static long frames=0;
static void service(){
    std::array<std::int32_t,GeneratedVariables::SavedCount> got{};
    if(mail->TakeSave(got)){disk=got;onDisk=true;}
    if(mail->TakeLoadRequest()&&onDisk) mail->PublishLoaded(disk);
}
static In pad(float x,float y,std::uint64_t b=0){return In{{x,y},static_cast<std::uint32_t>(b)};}
static void step(In a=In{},In b=In{}){g->Update(1.0/60.0,{a,b,In{},In{}});service();++frames;}
static void idle(int n){for(int i=0;i<n;++i)step();}
static void press(std::uint64_t b){step(pad(0,0,b));step();}
static void press2(std::uint64_t b){step(In{},pad(0,0,b));step();}
static void push(float x,float y){step(pad(x,y));step();}
static void push2(float x,float y){step(In{},pad(x,y));step();}
static std::int32_t gv(std::size_t i){return g->Variable(i);}
static std::int32_t pv(int p,std::size_t i){g->SetCurrentPlayer(static_cast<std::size_t>(p-1));auto v=g->PlayerVariable(i);g->SetCurrentPlayer(0);return v;}
static void setpv(int p,std::size_t i,std::int32_t v){g->SetCurrentPlayer(static_cast<std::size_t>(p-1));g->SetPlayerVariable(i,v);g->SetCurrentPlayer(0);}
static std::int32_t cv(std::size_t item,std::size_t i){g->SetSelf(item);auto v=g->CopyVariable(i);g->SetSelf(g->NoItem());return v;}
static SceneState::Position at(std::size_t i){return g->Current()[i];}
static bool seen(std::size_t i){return g->CurrentVisibility()[i];}
static void put(std::size_t i,float x,float y){g->SetPosition(i,x,y);}
static int aliveCount(std::size_t first,int n){int c=0;for(int k=0;k<n;++k)c+=g->Alive(first+static_cast<std::size_t>(k))?1:0;return c;}
static constexpr float T=64.f;
// Leaves the scene by pushing one way from where the hero is put, until the scene changes.
static bool leave(std::size_t hero,float x,float y,float dx,float dy){
    const auto scene=g->CurrentScene(); put(hero,x,y); step();
    for(int i=0;i<240&&g->CurrentScene()==scene;++i) step(pad(dx,dy));
    idle(2); return g->CurrentScene()!=scene;
}
// Fights the nearest live copy of a template as a warrior: stands to its left, faces right, and swings.
static bool fight(std::size_t first,int n,std::size_t hero,int limit=1500){
    std::size_t target=g->NoItem(); float best=1e9f;
    for(int k=0;k<n;++k){const auto c=first+static_cast<std::size_t>(k); if(!g->Alive(c)) continue; const float d=g->Distance(c,hero); if(d<best){best=d;target=c;}}
    if(target==g->NoItem()) return false;
    for(int i=0;i<limit&&g->Alive(target);++i){
        const auto q=at(target); put(hero,q[0]-90.f,q[1]); step(pad(1,0)); step(pad(0,0,Buttons::Square)); idle(24);
    }
    return !g->Alive(target);
}
static std::size_t firstAlive(std::size_t first,int n){for(int k=0;k<n;++k)if(g->Alive(first+static_cast<std::size_t>(k)))return first+static_cast<std::size_t>(k);return g->NoItem();}
#ifdef SHOTS
static void shot(const char* name){
    std::ofstream f(std::string("@HERE@/shots6/")+name+".txt");
    const auto& info=g->CurrentSceneInfo(); const auto c=g->Camera();
    f<<g->CurrentScene()<<' '<<c.x<<' '<<c.y<<'\n';
    for(std::size_t i=info.firstItem;i<info.firstItem+info.itemCount;++i){
        const auto p=g->Current()[i];
        f<<"i "<<(i-info.firstItem)<<' '<<p[0]<<' '<<p[1]<<' '<<(g->CurrentVisibility()[i]?1:0)<<' '<<g->SpriteFrame(i)<<' '<<(g->Flipped(i)?1:0)<<'\n';
        const auto t=g->CurrentText(i); f<<"t "<<t<<'\n';
        for(const auto& q:g->ParticleQuads(i)) f<<"q "<<(i-info.firstItem)<<' '<<q.x<<' '<<q.y<<' '<<q.width<<' '<<q.height<<' '<<q.color.red<<' '<<q.color.green<<' '<<q.color.blue<<'\n';
    }
}
#define SHOT(n) shot(n)
#else
#define SHOT(n)
#endif
int main(){
    auto box=std::make_unique<SceneState::SaveMailbox>(); mail=box.get();
    auto owned=std::make_unique<SceneState>(1920,1080,nullptr,box.get()); g=owned.get(); auto& scene=*owned;
    idle(3);
    CHECK(scene.CurrentScene()==S_title,"starts on the title"); SHOT("01-title");
    press(Buttons::Cross); idle(2);
    CHECK(scene.CurrentScene()==S_story&&gv(G_gold)==10&&pv(1,P_n0)==18&&pv(1,P_nlen)==5,"New game: the story, 10 gold, and player 1 called ROWAN");
    CHECK(seen(I_story_story0)&&seen(I_story_st0a)&&!seen(I_story_story1),"the first page of the story shows"); SHOT("02-story");
    for(int k=0;k<3;++k) press(Buttons::Cross);
    CHECK(gv(G_page)==3&&seen(I_story_story3),"three presses later, the last page");
    press(Buttons::Cross); idle(2);
    CHECK(scene.CurrentScene()==S_create,"the story ends in making a character");
    // player 1 makes a warrior with their own look and name
    push(1,0); CHECK(pv(1,P_cls)==2&&seen(I_create_ccls1_1),"right turns the class to Ranger");
    push(-1,0); CHECK(pv(1,P_cls)==1&&seen(I_create_ccls0_1)&&seen(I_create_cclsd0_1),"left turns it back to Warrior, with its words");
    push(-1,0); CHECK(pv(1,P_cls)==3,"left from Warrior goes round to Mage"); push(1,0);
    push(0,1); push(1,0); CHECK(pv(1,P_crow)==1&&pv(1,P_skin)==1,"down to Skin, right picks the second skin");
    push(0,1); push(1,0); push(0,1); push(1,0); push(0,1); push(-1,0);
    CHECK(pv(1,P_outfit)==1&&pv(1,P_hstyle)==1&&pv(1,P_hcolor)==2,"clothes, hair style and hair color change");
    push(0,1); press(Buttons::Cross); CHECK(pv(1,P_crow)==5&&pv(1,P_cgrid)==1&&seen(I_create_cletters1),"X on Name opens the letter grid");
    push(0,1); press(Buttons::Cross); CHECK(pv(1,P_nlen)==6&&pv(1,P_n5)==11,"down and X adds a K");
    SHOT("03-create");
    push(0,1); push(0,1); for(int k=0;k<6;++k) push(1,0);
    CHECK(pv(1,P_cgx)==6&&pv(1,P_cgy)==3&&seen(I_create_ccell2_1),"the cursor reaches the wide rub-out cell");
    press(Buttons::Cross); CHECK(pv(1,P_nlen)==5&&pv(1,P_n5)==0,"rub-out takes the K away");
    push(1,0); push(1,0); press(Buttons::Cross); CHECK(pv(1,P_cgrid)==0,"OK closes the grid");
    // player 2 joins here and makes a mage
    press2(Buttons::Cross); idle(1);
    CHECK(scene.PlayersHere()==2&&seen(I_create_cpanel2)&&pv(2,P_n0)==23&&!seen(I_create_p2create),"player 2 presses X, joins as WREN and gets their own panel");
    push2(1,0); push2(1,0); CHECK(pv(2,P_cls)==3,"player 2 picks Mage");
    for(int k=0;k<6;++k) push2(0,1);
    press2(Buttons::Cross); idle(1); CHECK(pv(2,P_cdone)==1&&seen(I_create_cok2)&&seen(I_create_cwait2),"player 2 is ready and waits");
    push(0,1); press(Buttons::Cross); idle(3);
    CHECK(scene.CurrentScene()==S_village,"both ready: off to the village");
    CHECK(pv(1,P_maxHp)==16&&pv(1,P_hp)==16&&pv(2,P_maxHp)==12&&pv(2,P_mp)==8,"a warrior has 16 health, a mage 12 and 8 mana");
    std::printf("debug vis h1 %d h2 %d h3 %d hair1 %d gear2 %d\n",seen(I_village_hero1),seen(I_village_hero2),seen(I_village_hero3),seen(I_village_hair1),seen(I_village_gear2));
    CHECK(seen(I_village_hero1)&&seen(I_village_hero2)&&!seen(I_village_hero3)&&seen(I_village_hair1)&&seen(I_village_gear2),"two players, each with hair and weapon");
    CHECK(scene.SpriteFrame(I_village_hero1)>=60&&scene.SpriteFrame(I_village_hair1)>=(1*4+2)*12&&scene.SpriteFrame(I_village_gear2)>=24,"each layer shows the chosen look");
    CHECK(seen(I_village_p2_panel)&&seen(I_village_p1_mp)==false,"player 2's card shows; player 1, a warrior, has no mana");
    { const std::string name(scene.CurrentText(I_village_p1_name)), hp(scene.CurrentText(I_village_p1_hp)), hp2(scene.CurrentText(I_village_p2_hp)), name2(scene.CurrentText(I_village_p2_name));
      std::printf("debug texts [%s] [%s] [%s] [%s] [%s]\n",name.c_str(),hp.c_str(),name2.c_str(),hp2.c_str(),std::string(scene.CurrentText(I_village_gslime_lv)).c_str());
      CHECK(name.rfind("ROWAN",0)==0&&hp=="16/16"&&name2.rfind("WREN",0)==0&&hp2=="12/12","the cards spell each player's name and health");
      CHECK(std::string(scene.CurrentText(I_village_gslime_lv)).rfind("Lv",0)==0&&seen(I_village_gslime_lv),"each slime carries its level tag"); }
    CHECK(aliveCount(I_village_gslime,3)==3,"three slimes in Mira's garden");
    SHOT("04-village");
    // Mira's quest
    const auto h1=I_village_hero1;
    put(h1,24*T,9.4f*T); idle(3); CHECK(seen(I_village_talk_mira),"the talk prompt shows by Mira");
    press(Buttons::Cross); CHECK(gv(G_dlg)==1&&seen(I_village_line_m1)&&seen(I_village_who_mira),"X opens Mira's first line"); SHOT("05-dialog");
    press(Buttons::Cross); press(Buttons::Cross); CHECK(gv(G_dlg)==3&&seen(I_village_line_m3),"X twice reaches her question");
    press(Buttons::Circle); CHECK(gv(G_dlg)==0&&gv(G_q1)==0,"Circle: not now");
    for(int k=0;k<4;++k) press(Buttons::Cross);
    CHECK(gv(G_q1)==1&&gv(G_dlg)==0&&seen(I_village_toast9),"X on her question accepts the quest");
    { // a ranger aims by themselves: standing above and to the side of a slime and facing away, the arrow still finds it
      const auto mark=firstAlive(I_village_gslime,3); const auto q=at(mark); const auto was=pv(1,P_cls); const auto hpWas=cv(mark,C_mhp);
      setpv(1,P_cls,2); setpv(1,P_atkCd,0); put(h1,q[0]-150.f,q[1]-190.f); step(pad(-1,0)); idle(2);
      step(pad(0,0,Buttons::Square)); idle(2);
      CHECK(cv(mark,C_mhp)<hpWas&&pv(1,P_face)==0,"a ranger's arrow hits the nearest creature, and the ranger turns to face it");
      setpv(1,P_atkCd,0); put(h1,q[0]-2000.f,q[1]); idle(3); const auto hpFar=cv(mark,C_mhp); step(pad(0,0,Buttons::Square)); idle(2);
      CHECK(!g->Alive(mark)||cv(mark,C_mhp)==hpFar,"but not one that is out of reach");
      setpv(1,P_cls,was); setpv(1,P_atkCd,0); idle(30); }
    for(int k=0;k<3&&aliveCount(I_village_gslime,3)>0;++k) fight(I_village_gslime,3,h1);
    CHECK(aliveCount(I_village_gslime,3)==0,"the three garden slimes are cut down");
    idle(2);
    CHECK(gv(G_gKills)==3&&gv(G_gardenClean)==1&&pv(1,P_xp)>=40,"three kills: the garden is clear and the warrior has xp");
    put(h1,24*T,9.4f*T); idle(2); press(Buttons::Cross); idle(1);
    CHECK(gv(G_q1)==2&&gv(G_gold)>=40&&gv(G_potion)==2,"Mira pays 30 gold and a potion");
    press(Buttons::Cross);
    // journal, skills, save
    press(Buttons::Options); CHECK(gv(G_mode)==1&&scene.Paused()&&gv(G_menuP)==1,"Options pauses");
    push(0,1); push(0,1); press(Buttons::Cross); idle(1);
    CHECK(gv(G_mode)==3&&seen(I_village_jq1)&&seen(I_village_jok1)&&!seen(I_village_jq2),"the journal lists Mira's garden as done"); SHOT("06-journal");
    press(Buttons::Circle); push(0,-1); press(Buttons::Cross); idle(1);
    CHECK(gv(G_mode)==2&&seen(I_village_cicon0_0)&&!seen(I_village_cicon2_0)&&seen(I_village_sn0_0),"the warrior sees the warrior's skills");
    const auto sp=pv(1,P_sp); press(Buttons::Cross); idle(1);
    CHECK(pv(1,P_sk0)==1&&pv(1,P_sp)==sp-1&&seen(I_village_own0),"Sharp Edge learned"); SHOT("07-skills");
    press(Buttons::Circle); push(0,1); push(0,1); press(Buttons::Cross); idle(2);
    CHECK(onDisk&&disk[G_q1]==2&&gv(G_toastK)==1&&gv(G_toastT)>0,"Save game writes the save and queues its note");
    press(Buttons::Circle); idle(1); CHECK(gv(G_mode)==0&&!scene.Paused(),"Circle resumes");
    // the bag
    press(Buttons::Triangle); idle(1); CHECK(gv(G_bag)==1&&seen(I_village_bag)&&seen(I_village_bag_pn),"Triangle opens the bag; no pet yet");
    setpv(1,P_hp,5); press(Buttons::Circle); idle(1); CHECK(pv(1,P_hp)==13&&gv(G_potion)==1,"Circle drinks a potion");
    SHOT("08-bag");
    press(Buttons::Triangle); idle(1); CHECK(gv(G_bag)==0,"Triangle closes the bag");
    // east to the meadow
    CHECK(leave(h1,38*T,12*T,1,0)&&scene.CurrentScene()==S_meadow,"the east road leads to the meadow");
    const auto m1=I_meadow_hero1;
    CHECK(gv(G_from)==1&&std::fabs(at(m1)[0]-2*T)<70.f&&seen(I_meadow_hero2),"both arrive at the west side");
    CHECK(aliveCount(I_meadow_slime,5)==5&&aliveCount(I_meadow_hopper,5)==5,"five slimes and five hoppers about");
    { const auto hammer=at(I_meadow_hammer_item); put(m1,hammer[0]-8.f,hammer[1]-8.f); idle(3); CHECK(gv(G_hammer)==1&&!seen(I_meadow_hammer_item)&&seen(I_meadow_toast5),"walking onto Tobin's hammer picks it up"); }
    { const auto hop=firstAlive(I_meadow_hopper,5); const auto q=at(hop); put(m1,q[0]-150.f,q[1]); idle(4); CHECK(cv(hop,C_mstate)==2,"a hopper runs from a player who comes near"); }
    { const auto sl=firstAlive(I_meadow_slime,5); const auto q=at(sl); const auto h2=I_meadow_hero2; put(h2,q[0]-250.f,q[1]); push2(1,0); const auto before=cv(sl,C_mhp); const auto mp=pv(2,P_mp);
      press2(Buttons::Square); CHECK(pv(2,P_mp)==mp-2&&aliveCount(I_meadow_fireball,6)==1,"the mage casts a fireball for 2 mana");
      put(I_meadow_hero2,q[0]-250.f,q[1]+300.f); idle(20); CHECK(cv(sl,C_mhp)<before||!g->Alive(sl),"it bursts by the slime and burns it"); SHOT("09-meadow"); }
    // north to Brookmere
    CHECK(leave(m1,23*T,1.5f*T,0,-1)&&scene.CurrentScene()==S_town,"the north road leads to Brookmere");
    const auto t1=I_town_hero1;
    CHECK(aliveCount(I_town_folk,6)==6,"six townsfolk walk about");
    put(t1,33*T,25.4f*T); idle(2); CHECK(seen(I_town_talk_pell),"Pell can be talked to");
    { const auto gold=gv(G_gold); press(Buttons::Cross); std::printf("debug dlg %d\n",gv(G_dlg)); press(Buttons::Cross); std::printf("debug dlg %d\n",gv(G_dlg)); press(Buttons::Cross); idle(2);
      std::printf("debug pet kind %d gold %d->%d alive %d\n",pv(1,P_petKind),gold,gv(G_gold),aliveCount(I_town_pet,4));
      CHECK(pv(1,P_petKind)==1&&gv(G_gold)==gold-20&&aliveCount(I_town_pet,4)==1,"20 gold buys a cat, and it appears");
      CHECK(cv(firstAlive(I_town_pet,4),C_owner)==1,"the cat is player 1's"); }
    { const auto gold=gv(G_gold); press(Buttons::Cross); press(Buttons::Cross); idle(1); CHECK(gv(G_treat)==3&&gv(G_gold)==gold-10,"3 treats for 10 gold"); }
    press(Buttons::Triangle); setpv(1,P_petHunger,10); press(Buttons::Square); idle(1);
    CHECK(gv(G_treat)==2&&pv(1,P_petHunger)==100&&pv(1,P_petXp)==5&&seen(I_town_bag_pc),"feeding the cat from the bag"); press(Buttons::Triangle);
    put(t1,24*T,11.4f*T); idle(2); press(Buttons::Cross); press(Buttons::Cross); press(Buttons::Cross); CHECK(gv(G_q4)==1&&gv(G_wolfKills)==0,"Captain Rhea's wolf quest accepted");
    put(t1,29*T,12.4f*T); idle(2); press(Buttons::Cross); press(Buttons::Cross); press(Buttons::Cross); CHECK(gv(G_q3)==1,"Odo's fur quest accepted");
    { idle(120); const auto pet=firstAlive(I_town_pet,4); CHECK(pet!=g->NoItem()&&g->Distance(pet,t1)<300.f,"the cat follows its owner"); } SHOT("10-town");
    // the forest: a wolf pack
    CHECK(leave(t1,22*T,26*T,0,1)&&scene.CurrentScene()==S_meadow,"south out of town");
    CHECK(leave(I_meadow_hero1,46*T,14*T,1,0)&&scene.CurrentScene()==S_forest,"east into the forest");
    const auto f1=I_forest_hero1;
    CHECK(aliveCount(I_forest_wolf,6)==6&&aliveCount(I_forest_boar,3)==3,"six wolves in two packs, three boars");
    setpv(1,P_level,15); idle(2);
    { const auto w=firstAlive(I_forest_wolf,6); const auto q=at(w); put(f1,q[0]-300.f,q[1]); idle(3); int angry=0; for(int k=0;k<6;++k) angry+=cv(I_forest_wolf+static_cast<std::size_t>(k),C_mstate)==1?1:0;
      CHECK(angry>=3,"wolves spot a player and the pack comes together"); }
    { const auto b=firstAlive(I_forest_boar,3); const auto q=at(b); put(f1,q[0]-300.f,q[1]); idle(3); CHECK(cv(b,C_mstate)==0,"a boar stays calm until it is hit"); }
    for(int k=0;k<5;++k){ fight(I_forest_wolf,6,f1); idle(2); if(gv(G_wolfKills)>=5) break; if(aliveCount(I_forest_wolf,6)==0) idle(320); }
    CHECK(gv(G_wolfKills)>=5,"five wolves defeated"); SHOT("11-forest");
    put(f1,(48-8)*T,11.4f*T); idle(2); press(Buttons::Cross); press(Buttons::Cross); press(Buttons::Cross); CHECK(gv(G_q5)==1,"Dunn asks for the Stone Warden");
    // the cave and its warden
    CHECK(leave(f1,44*T,13*T,1,0)&&scene.CurrentScene()==S_cave,"the cave mouth leads inside");
    const auto c1=I_cave_hero1;
    CHECK(aliveCount(I_cave_warden,1)==1&&aliveCount(I_cave_bat,8)==8,"the Warden waits, and eight bats");
    CHECK(fight(I_cave_warden,1,c1,3000),"the Stone Warden falls");
    idle(2); CHECK(gv(G_wardenDead)==1&&seen(I_cave_toast12),"the game knows the Warden is gone"); SHOT("12-cave");
    CHECK(leave(c1,1*T,12*T,-1,0)&&scene.CurrentScene()==S_forest,"back out of the cave");
    put(I_forest_hero1,(48-8)*T,11.4f*T); idle(2); { const auto gold=gv(G_gold); press(Buttons::Cross); idle(2);
      CHECK(gv(G_q5)==2&&gv(G_gold)==gold+100&&seen(I_forest_peace),"Dunn: the dew fades, 100 gold"); }
    press(Buttons::Cross);
    // fainting
    { const auto gold=gv(G_gold); setpv(1,P_hp,0); idle(2); CHECK(pv(1,P_hp)==pv(1,P_maxHp)&&gv(G_gold)==gold-gold/10&&seen(I_forest_toast8),"a fainted player wakes up, minus a tenth of the gold"); }
    // save, quit, continue
    press(Buttons::Options); push(0,1); push(0,1); push(0,1); press(Buttons::Cross); idle(2);
    CHECK(onDisk&&disk[G_where]==5&&disk[G_wardenDead]==1,"saved in the forest");
    push(0,1); press(Buttons::Cross); idle(4); CHECK(scene.CurrentScene()==S_title&&gv(G_hasSave)==1&&seen(I_title_t_cont),"Quit to title finds the save");
    push(0,1); press(Buttons::Cross); idle(3);
    CHECK(scene.CurrentScene()==S_forest&&pv(1,P_level)==15&&pv(1,P_petKind)==1&&pv(2,P_cls)==3&&gv(G_q5)==2,"Continue brings back the forest, both players' characters and the cat");
    CHECK(aliveCount(I_forest_pet,4)==1,"the cat comes along after loading");
    const auto before=allocations;
    for(int i=0;i<600;++i) step(pad(i%120<60?1.f:-1.f,0,(i%30==0)?Buttons::Square:0),pad(0,i%90<45?1.f:-1.f,(i%40==0)?Buttons::Square:0));
    CHECK(allocations==before,"600 frames of two players fighting allocate nothing");
    std::printf("frames %ld, about %ld seconds of play\n%s\n",frames,frames/60,failures?"PLAYTHROUGH FAILED":"PLAYTHROUGH PASSED");
    return failures?1:0;
}
'''
open(f'{HERE}/bot6.cpp', 'w').write(src.replace('@ROOT@', root).replace('@IDS@', defs).replace('@HERE@', HERE))
