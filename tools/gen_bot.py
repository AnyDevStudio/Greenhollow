import json,sys
ids=json.load(open('ids.json')); root=sys.argv[1]
var=''.join(f'constexpr std::size_t V_{k}={v};\n' for k,v in ids['vars'].items())
it=''.join(f"constexpr std::size_t I_{k.replace('.','_')}={v};\n" for k,v in ids['items'].items())
sc=''.join(f'constexpr std::size_t S_{k}={v};\n' for k,v in ids['scenes'].items())
src=r'''
#include "Scene/SceneState.hpp"
#include "Input/Buttons.hpp"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <new>
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
static SceneState* g;
static long frames=0;
static void step(SceneState::Position d={0.f,0.f},std::uint32_t b=0){g->Update(1.0/60.0,d,b);++frames;}
static void idle(int n){for(int i=0;i<n;++i)step();}
static void press(std::uint32_t b){step({0.f,0.f},b);step();}
static std::int32_t v(std::size_t i){return g->Variable(i);}
static SceneState::Position at(std::size_t i){return g->Current()[i];}
static bool seen(std::size_t i){return g->CurrentVisibility()[i];}
// Walks like a player, one axis at a time. False when the walk took too long, which means something blocked it.
static bool walk(std::size_t hero,float x,float y,bool yFirst=false,bool leaves=false,int limit=1500){
    const auto scene=g->CurrentScene();
    for(int i=0;i<limit;++i){
        if(g->CurrentScene()!=scene) return leaves;
        const auto p=at(hero); const float dx=x-p[0],dy=y-p[1];
        const bool xDone=std::fabs(dx)<8.f,yDone=std::fabs(dy)<8.f;
        if(xDone&&yDone){step();return true;}
        bool useY=yFirst?!yDone:xDone;
        if(useY) step({0.f,dy>0?1.f:-1.f}); else step({dx>0?1.f:-1.f,0.f});
    }
    return false;
}
static constexpr float T=64.f;
static void killSlime(int n,std::size_t slime,std::size_t drop,std::size_t hp,std::size_t hero){
    for(int i=0;i<900 && g->Distance(slime,hero)>130.f;++i) step();
    char m[80]; std::snprintf(m,80,"slime %d came to the hero",n); CHECK(g->Distance(slime,hero)<=130.f,m);
    int swings=0;
    for(int i=0;i<300 && v(hp)>0;++i){ step({0.f,0.f},Buttons::Square); step(); ++swings; idle(22); }
    std::snprintf(m,80,"slime %d died in %d swings",n,swings); CHECK(v(hp)<=0 && swings==3,m);
    std::snprintf(m,80,"slime %d is gone and dropped jelly",n); CHECK(!seen(slime)&&seen(drop),m);
    const auto before=v(V_jelly);
    const auto d=at(drop);
    for(int i=0;i<200 && v(V_jelly)==before;++i){ const auto p=at(hero); const float dx=d[0]-p[0],dy=d[1]-p[1]; const float l=std::hypot(dx,dy); step({dx/(l+.001f),dy/(l+.001f)}); }
    std::snprintf(m,80,"picked up jelly from slime %d",n); CHECK(v(V_jelly)==before+1&&!seen(drop),m);
}
int main(){
    SceneState scene(1920,1080); g=&scene;
    idle(2);
    CHECK(scene.CurrentScene()==S_village,"starts in the village");
    CHECK(v(V_hp)==10&&v(V_level)==1&&v(V_quest)==0,"starts level 1 with 10 hp and no quest");
    CHECK(!seen(I_village_bag)&&!seen(I_village_dlg_panel)&&!seen(I_village_banner),"bag, dialog and banner start hidden");
    const auto hv=I_village_hero;
    // walls and animation
    CHECK(walk(hv,9*T,10*T),"walks to the front of the house");
    for(int i=0;i<90;++i) step({0.f,-1.f});
    CHECK(at(hv)[1]==8*T,"the house wall stops the hero");
    { const auto f=scene.SpriteFrame(hv); CHECK(f>=5&&f<=7,"walking up plays the up animation"); }
    idle(3); CHECK(scene.SpriteFrame(hv)==4,"standing still shows the idle frame facing up");
    step({-1.f,0.f}); CHECK(scene.Flipped(hv),"walking left mirrors the hero"); step({1.f,0.f}); CHECK(!scene.Flipped(hv),"walking right unmirrors the hero");
    // quest giver
    CHECK(walk(hv,21*T,10*T,true),"walks to Mira");
    idle(2); CHECK(seen(I_village_talk),"talk prompt shows near Mira");
    press(Buttons::Cross); CHECK(v(V_dlg)==1&&seen(I_village_line1)&&seen(I_village_dlg_panel),"X opens the first line");
    press(Buttons::Cross); CHECK(v(V_dlg)==2&&seen(I_village_line2)&&!seen(I_village_line1),"X goes to the second line");
    press(Buttons::Cross); CHECK(v(V_dlg)==3,"X reaches the question");
    press(Buttons::Circle); CHECK(v(V_dlg)==0&&v(V_quest)==0,"Circle says not now and takes no quest");
    press(Buttons::Cross); press(Buttons::Cross); press(Buttons::Cross); press(Buttons::Cross);
    CHECK(v(V_quest)==1&&v(V_dlg)==4,"X on the question accepts the quest");
    idle(2); CHECK(seen(I_village_quest_panel),"the quest tracker appears");
    press(Buttons::Cross); CHECK(v(V_dlg)==0,"X closes the dialog");
    press(Buttons::Cross); CHECK(v(V_dlg)==5,"talking again before the jelly says keep hunting");
    press(Buttons::Cross);
    press(Buttons::Cross); CHECK(v(V_dlg)==5,"reopened"); CHECK(walk(hv,21*T,15*T,true),"walks away from Mira");
    idle(2); CHECK(v(V_dlg)==0,"walking away closes the dialog");
    // to the woods
    CHECK(walk(hv,39.5f*T,12*T,true,true),"walks through the east gate");
    idle(2); CHECK(scene.CurrentScene()==S_forest,"east gate goes to the forest");
    const auto hf=I_forest_hero;
    CHECK(at(hf)[0]==3*T,"the hero starts at the west side of the forest");
    CHECK(walk(hf,12*T,13*T),"walks to the first slime");
    killSlime(1,I_forest_slime1,I_forest_drop1,V_s1,hf);
    CHECK(v(V_xp)==30,"a kill gives 30 xp");
    CHECK(walk(hf,20*T,14*T,true),"walks to the second slime");
    killSlime(2,I_forest_slime2,I_forest_drop2,V_s2,hf);
    CHECK(walk(hf,30*T,13*T,true),"walks to the third slime");
    killSlime(3,I_forest_slime3,I_forest_drop3,V_s3,hf);
    CHECK(v(V_jelly)==3&&v(V_xp)==90&&v(V_level)==1,"three jellies, 90 xp, still level 1");
    CHECK(v(V_hp)>0,"the hero survived the fight"); std::printf("      hp left %d of %d\n",v(V_hp),v(V_maxHp));
    { const auto p=at(hf); (void)p; }
    scene.SetVariable(V_hp,500); idle(430); CHECK(seen(I_forest_slime1)&&v(V_s1)==3,"a dead slime comes back after a while"); scene.SetVariable(V_hp,10);
    CHECK(walk(hf,3*T,13*T,true),"walks back along the path");
    CHECK(walk(hf,-1.f,13*T,false,true),"leaves by the west exit");
    idle(2); CHECK(scene.CurrentScene()==S_village,"the west exit goes home");
    CHECK(at(hv)[0]==36*T&&at(hv)[1]==12*T,"arrives at the east gate of the village");
    CHECK(walk(hv,21*T,12*T),"walks back to Mira"); CHECK(walk(hv,21*T,10*T),"stands in front of Mira");
    press(Buttons::Cross); idle(1);
    CHECK(v(V_quest)==2&&v(V_dlg)==6&&v(V_jelly)==0,"handing in takes the jellies and finishes the quest");
    CHECK(v(V_gold)==50&&v(V_potion)==1,"the reward is 50 gold and a potion");
    CHECK(v(V_level)==2&&v(V_xp)==90&&v(V_xpNeed)==200,"the quest xp raises the hero to level 2 with 90 left over");
    CHECK(v(V_maxHp)==12&&v(V_hp)==12&&v(V_atk)==2,"level 2 has 12 hp and 2 attack");
    idle(2); CHECK(seen(I_village_banner),"LEVEL UP shows");
    press(Buttons::Cross); press(Buttons::Cross); CHECK(v(V_dlg)==7,"after the quest she only says thanks"); press(Buttons::Cross);
    // bag
    press(Buttons::Triangle); idle(1); CHECK(v(V_bag)==1&&seen(I_village_bag)&&seen(I_village_bag_q2),"Triangle opens the bag and it shows the finished quest");
    scene.SetVariable(V_hp,3); press(Buttons::Circle); CHECK(v(V_hp)==8&&v(V_potion)==0,"Circle drinks a potion for 5 hp");
    scene.SetVariable(V_potion,1); scene.SetVariable(V_hp,10); press(Buttons::Circle); CHECK(v(V_hp)==12,"a potion cannot go over max hp");
    press(Buttons::Circle); CHECK(v(V_hp)==12,"no potion left, nothing happens");
    press(Buttons::Triangle); idle(1); CHECK(v(V_bag)==0&&!seen(I_village_bag),"Triangle closes the bag");
    // house
    CHECK(walk(hv,21*T,11*T),"back on the path"); CHECK(walk(hv,11*T,11*T),"walks to the house"); CHECK(walk(hv,11*T,8.2f*T,true,true),"steps on the doormat");
    idle(2); CHECK(scene.CurrentScene()==S_house,"the door goes into the house");
    const auto hh=I_house_hero;
    CHECK(walk(hh,15*T,7*T,true),"walks into the room"); CHECK(walk(hh,19*T,7*T),"walks to Tobin");
    idle(2); CHECK(seen(I_house_talk),"talk prompt shows near Tobin");
    press(Buttons::Cross); CHECK(v(V_dlg)==1&&seen(I_house_line1),"Tobin talks"); press(Buttons::Cross); CHECK(v(V_dlg)==0,"X closes it");
    CHECK(walk(hh,11*T,7*T),"walks to the bed side"); CHECK(walk(hh,11*T,4.5f*T,true),"stands by the bed");
    idle(2); CHECK(seen(I_house_sleep),"sleep prompt shows");
    scene.SetVariable(V_hp,1); press(Buttons::Cross); CHECK(v(V_hp)==12&&seen(I_house_rest),"the bed restores hp");
    CHECK(walk(hh,15.5f*T,7*T,true),"walks to the door side"); CHECK(walk(hh,15.5f*T,14.5f*T,true,true),"leaves by the door mat");
    idle(2); CHECK(scene.CurrentScene()==S_village,"the mat goes back outside");
    CHECK(at(hv)[0]==11*T&&at(hv)[1]==10*T,"comes out in front of the door");
    // dying
    CHECK(walk(hv,11*T,12*T,true),"to the road"); CHECK(walk(hv,39.5f*T,12*T,true,true),"back to the gate"); idle(2);
    CHECK(scene.CurrentScene()==S_forest,"in the forest again");
    CHECK(seen(I_forest_slime1)&&v(V_s1)==3,"slimes are back");
    CHECK(walk(hf,12*T,13*T),"goes to a slime");
    scene.SetVariable(V_hp,1);
    for(int i=0;i<1200&&scene.CurrentScene()==S_forest;++i) step();
    idle(2);
    CHECK(scene.CurrentScene()==S_village&&v(V_hp)==12&&seen(I_village_faint),"falling in battle wakes the hero in the village");
    CHECK(at(hv)[0]==21*T&&at(hv)[1]==10*T,"wakes up beside Mira");
    // no allocation while the game runs
    const auto before=allocations;
    for(int i=0;i<600;++i) step({1.f,0.f},Buttons::Square);
    CHECK(allocations==before,"600 frames of play allocate nothing");
    std::printf("frames %ld, about %ld seconds of play\n%s\n",frames,frames/60,failures?"PLAYTHROUGH FAILED":"PLAYTHROUGH PASSED");
    return failures?1:0;
}
'''
open('bot.cpp','w').write(src.replace('@ROOT@',root).replace('@IDS@',var+it+sc))
