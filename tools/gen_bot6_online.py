# Writes bot_online.cpp: two consoles play Greenhollow together over the network of this computer. One hosts and
# runs the game; the other joins as a friend, only sends its controller and shows the screen the host makes for it.
# The two share the start of gen_bot6.py's program: the loader for the tile maps and the names of things.
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(f'{HERE}/ids6.json')); root = sys.argv[1]
defs = ''.join(f'constexpr std::size_t G_{k}={v};\n' for k, v in ids['game'].items() if k != 'from')
defs += f"constexpr std::size_t G_from={ids['game']['from']};\n"
defs += ''.join(f'constexpr std::size_t P_{k}={v};\n' for k, v in ids['player'].items())
defs += ''.join(f"constexpr std::size_t I_{k.replace('.', '_').replace('~', '_')}={v};\n" for k, v in ids['items'].items())
defs += ''.join(f'constexpr std::size_t S_{k}={v};\n' for k, v in ids['scenes'].items())
first = open(f'{HERE}/gen_bot6.py').read()
head = first[first.index("src = r'''") + len("src = r'''"):first.index('static int failures=0;')].replace('@IDS@', defs).replace('@ROOT@', root)
body = r'''
#include "Online/OnlinePlay.hpp"
static int failures=0;
#define CHECK(c,msg) do{ bool ok=(c); std::printf("%s  %s\n",ok?"ok  ":"FAIL",msg); if(!ok)++failures; }while(0)
using In=SceneState::PlayerInput;
static In pad(float x,float y,std::uint64_t b=0){return In{{x,y},static_cast<std::uint32_t>(b)};}
static std::unique_ptr<SceneState> hostScene, friendScene;
static std::unique_ptr<OnlinePlay> hostPlay, friendPlay;
static std::uint64_t now=1000;
static long frames=0;
// One frame on both consoles: the host's, then the friend's.
static void frame(In h=In{},In f=In{}){
    now+=16; ++frames;
    hostPlay->BeforeFrame(*hostScene,now,h); hostScene->Update(1.0/60.0,{h,In{},In{},In{}}); hostPlay->AfterFrame(*hostScene);
    friendPlay->BeforeFrame(*friendScene,now,f); friendScene->Update(1.0/60.0,{friendScene->Mirroring()?In{}:f,In{},In{},In{}});
}
static void idle(int n){for(int i=0;i<n;++i)frame();}
template <typename Done> static bool until(Done done,int limit=600){for(int i=0;i<limit&&!done();++i)frame();return done();}
static void hpress(std::uint64_t b){frame(pad(0,0,b));frame();}
static void hpush(float x,float y){frame(pad(x,y));frame();}
// The friend's controller goes over the network, so what it does shows a few frames later.
static void fpress(std::uint64_t b){frame(In{},pad(0,0,b));idle(4);}
static void fpush(float x,float y){frame(In{},pad(x,y));idle(4);}
static std::int32_t pv(int p,std::size_t i){hostScene->SetCurrentPlayer(static_cast<std::size_t>(p-1));auto v=hostScene->PlayerVariable(i);hostScene->RestorePlayer(0,false);return v;}
static bool hsees(std::size_t i){return hostScene->CurrentVisibility()[i];}
static bool fsees(std::size_t i){return friendScene->CurrentVisibility()[i];}
static float hx(std::size_t i){return hostScene->Current()[i][0];}
static float fx(std::size_t i){return friendScene->Current()[i][0];}
// Saves what one console shows, for tools/render6.py to draw: the pictures of two consoles side by side.
static void shot(const SceneState& scene,const std::string& name){
    std::ofstream f(std::string("@HERE@/shots_online/")+name+".txt");
    const auto& info=scene.CurrentSceneInfo(); const auto c=scene.Camera();
    f<<scene.CurrentScene()<<' '<<c.x<<' '<<c.y<<'\n';
    for(std::size_t i=info.firstItem;i<info.firstItem+info.itemCount;++i){
        const auto p=scene.Current()[i];
        f<<"i "<<(i-info.firstItem)<<' '<<p[0]<<' '<<p[1]<<' '<<(scene.CurrentVisibility()[i]?1:0)<<' '<<scene.SpriteFrame(i)<<' '<<(scene.Flipped(i)?1:0)<<'\n';
        const auto t=scene.CurrentText(i); f<<"t "<<t<<'\n';
        for(const auto& q:scene.ParticleQuads(i)) f<<"q "<<(i-info.firstItem)<<' '<<q.x<<' '<<q.y<<' '<<q.width<<' '<<q.height<<' '<<q.color.red<<' '<<q.color.green<<' '<<q.color.blue<<'\n';
    }
}
static void shots(const char* name){shot(*hostScene,std::string(name)+"-host");shot(*friendScene,std::string(name)+"-friend");}
// What a text shows, without the blanks a short name leaves behind it.
static std::string words(const SceneState& scene,std::size_t i){std::string t(scene.CurrentText(i));while(!t.empty()&&t.back()==' ')t.pop_back();return t;}

int main(){
    hostScene=std::make_unique<SceneState>(1920,1080); friendScene=std::make_unique<SceneState>(1920,1080);
    hostPlay=std::make_unique<OnlinePlay>(OnlinePlay::Settings{0x6877,1,47811,47810,Lan::Loopback});
    friendPlay=std::make_unique<OnlinePlay>(OnlinePlay::Settings{0x6877,2,47811,47810,Lan::Loopback});
    auto& H=*hostScene; auto& F=*friendScene;
    idle(3);
    CHECK(H.CurrentScene()==S_title&&F.CurrentScene()==S_title,"both consoles start on the title");

    // the host starts a new game and walks into the village
    hpress(Buttons::Cross); idle(2); hpress(Buttons::Options); idle(2);
    CHECK(H.CurrentScene()==S_create,"host: new game, the story skipped, making a character");
    hpush(0,-1); hpress(Buttons::Cross); idle(3);
    CHECK(H.CurrentScene()==S_village&&pv(1,P_made)==1,"host: ready, and in the village");
    idle(2);
    CHECK(H.OnlineState()==1,"the village lets friends join");

    // the friend chooses Join a friend
    frame(In{},pad(0,1)); idle(2);
    CHECK(F.Variable(G_sel)==2,"friend: down steps over Continue, which has no save, to Join a friend");
    frame(In{},pad(0,0,Buttons::Cross)); idle(3);
    CHECK(F.OnlineState()==2&&fsees(I_title_t_look),"friend: looking for a game, and the title says so");
    shots("1-join");
    CHECK(until([&]{return F.Mirroring()&&H.ScreensOpen()==2;}),"the friend finds the host and joins");
    CHECK(H.OnlineState()==1&&F.OnlineState()==3&&H.ScreenPlayer(1)==3,"the host hosts, the friend plays as player 4 on a screen of their own");

    // a friend with no character makes one, alone, while the host stays in the village
    CHECK(until([&]{return F.CurrentScene()==S_create;}),"the friend is taken to make a character");
    idle(4);
    CHECK(H.ScreenScene(1)==S_create&&H.CurrentScene()==S_village,"the host stays in the village meanwhile");
    CHECK(fsees(I_create_cpanel1)&&!fsees(I_create_cpanel2)&&!fsees(I_create_p2create),"the friend sees one panel, their own, and no invitation for a second controller");
    CHECK(words(F,I_create_cname1)=="JOS","their name starts as JOS, player 4's");
    fpush(1,0); fpush(1,0);
    CHECK(pv(4,P_cls)==3&&fsees(I_create_ccls2_1),"right twice on the friend's controller: Mage, on the host and on their screen");
    shots("2-create");
    fpush(0,-1); fpress(Buttons::Cross);
    CHECK(until([&]{return F.CurrentScene()==S_village;}),"friend ready: into the village, where the host already is");
    idle(4);
    CHECK(H.ScreenScene(1)==S_village&&pv(4,P_made)==1&&hsees(I_village_hero4)&&hsees(I_village_hero1),"the host sees both characters");
    CHECK(fsees(I_village_hero4)&&fsees(I_village_hero1)&&fx(I_village_hero4)==hx(I_village_hero4),"so does the friend, in the same places");
    CHECK(words(F,I_village_p1_name)=="JOS"&&words(H,I_village_p1_name)=="ROWAN","each screen's card shows its own player");
    CHECK(!fsees(I_village_p2_panel)&&!hsees(I_village_p2_panel)&&!fsees(I_village_pause_panel)&&!fsees(I_village_bag),"no second card and no menus on either");

    // the friend's menu is theirs alone, and stops nothing
    fpress(Buttons::Options);
    CHECK(until([&]{return fsees(I_village_pause_panel);})&&!hsees(I_village_pause_panel),"the friend opens the menu: it shows on their screen only");
    const float before=hx(I_village_hero1);
    for(int i=0;i<12;++i) frame(pad(1,0));
    CHECK(hx(I_village_hero1)>before+20,"the host keeps walking: a friend's menu does not stop the world");
    idle(4); shots("3-menu");
    fpress(Buttons::Circle);
    CHECK(until([&]{return !fsees(I_village_pause_panel);}),"O closes it");
    fpress(Buttons::Triangle);
    CHECK(until([&]{return fsees(I_village_bag);})&&!hsees(I_village_bag),"the friend's bag is theirs alone too");
    fpress(Buttons::Triangle);
    CHECK(until([&]{return !fsees(I_village_bag);}),"and closes");

    // the friend walks out to the meadow; the host stays
    const auto gate=H.Current()[I_village_gate];
    H.SetPosition(I_village_hero4,gate[0]-140,gate[1]+120);
    bool left=false;
    for(int i=0;i<300&&!left;++i){frame(In{},pad(1,0));left=H.ScreenScene(1)==S_meadow;}
    CHECK(left&&H.CurrentScene()==S_village,"the friend walks east into the meadow; the host is still in the village");
    CHECK(until([&]{return F.CurrentScene()==S_meadow;})&&fsees(I_meadow_hero4),"the friend's console shows the meadow");
    idle(3);
    CHECK(!hsees(I_village_hero4),"their character has left the village");
    const float hostWas=hx(I_village_hero1); const float friendWas=H.Current()[I_meadow_hero4][0];
    for(int i=0;i<20;++i) frame(pad(-1,0),pad(1,0));
    idle(4);
    CHECK(hx(I_village_hero1)<hostWas-20&&H.Current()[I_meadow_hero4][0]>friendWas+20,"both places run at once: each walks in their own");
    shots("4-apart");

    // the host follows
    H.SetPosition(I_village_hero1,gate[0]-140,gate[1]+120);
    bool came=false;
    for(int i=0;i<300&&!came;++i){frame(pad(1,0));came=H.CurrentScene()==S_meadow;}
    idle(6);
    CHECK(came&&hsees(I_meadow_hero1)&&hsees(I_meadow_hero4)&&fsees(I_meadow_hero1)&&fsees(I_meadow_hero4),"the host walks in after them: together again, and the meadow did not start over");
    shots("5-together");
    CHECK(H.Current()[I_meadow_hero4][0]>friendWas+20,"the friend is where they had walked to");
    for(int i=0;i<500&&F.Camera().x<=H.Camera().x+100;++i) frame(In{},pad(1,0)); // far enough east that the camera leaves the map's edge
    idle(4);
    CHECK(F.Camera().x>H.Camera().x+100,"each screen's camera follows its own character");
    fpress(Buttons::Triangle); until([&]{return fsees(I_meadow_bag);}); idle(4); shots("6-bag"); fpress(Buttons::Triangle); until([&]{return !fsees(I_meadow_bag);});

    // the friend leaves from their own menu
    fpress(Buttons::Options);
    CHECK(until([&]{return fsees(I_meadow_pause_panel);}),"the friend opens the menu in the meadow");
    fpush(0,-1); fpress(Buttons::Cross);
    CHECK(until([&]{return !F.Mirroring()&&H.ScreensOpen()==1;}),"Quit to title on the friend's menu sends only the friend home");
    idle(3);
    CHECK(F.CurrentScene()==S_title&&F.OnlineState()==0&&H.OnlineState()==1&&H.CurrentScene()==S_meadow&&!hsees(I_meadow_hero4),"the friend is on their title; the host plays on, without their character");

    // and comes back as the same character
    frame(In{},pad(0,1)); idle(2); frame(In{},pad(0,0,Buttons::Cross)); idle(3);
    CHECK(until([&]{return F.Mirroring()&&F.CurrentScene()==S_meadow;}),"the friend joins again and lands where the host is");
    idle(4);
    CHECK(pv(4,P_cls)==3&&pv(4,P_made)==1&&hsees(I_meadow_hero4)&&words(F,I_meadow_p1_name)=="JOS","still the Mage they made, straight into the game");

    // the host quits to the title: the game closes to friends, and the friend is sent home
    hpress(Buttons::Options); idle(2);
    CHECK(hsees(I_meadow_pause_panel)&&!fsees(I_meadow_pause_panel),"the host's menu is the host's alone");
    hpush(0,-1); hpress(Buttons::Cross);
    CHECK(until([&]{return H.CurrentScene()==S_title&&!F.Mirroring()&&H.ScreensOpen()==1;}),"the host quits to the title: the friend's game ends too");
    idle(3);
    CHECK(H.OnlineState()==0&&F.OnlineState()==0&&F.CurrentScene()==S_title,"nobody is online any more, and both are on their titles");

    // looking with nobody hosting: after ten seconds the title says what to check, and O stops looking
    frame(In{},pad(0,1)); idle(2); frame(In{},pad(0,0,Buttons::Cross)); idle(30);
    CHECK(F.OnlineState()==2&&fsees(I_title_t_look)&&!fsees(I_title_t_lookhint),"looking again, with no game to find: no hint at first");
    idle(600);
    CHECK(F.OnlineState()==2&&fsees(I_title_t_lookhint)&&!fsees(I_title_t_p2),"ten seconds later the title says what to check");
    frame(In{},pad(0,0,Buttons::Circle)); idle(4);
    CHECK(F.OnlineState()==0&&!fsees(I_title_t_look)&&!fsees(I_title_t_lookhint),"O stops looking, and the hint goes");

    std::printf("frames %ld\n%s\n",frames,failures?"ONLINE PLAYTHROUGH FAILED":"ONLINE PLAYTHROUGH PASSED");
    return failures?1:0;
}
'''
os.makedirs(f'{HERE}/shots_online', exist_ok=True)
open(f'{HERE}/bot_online.cpp', 'w').write(head + body.replace('@HERE@', HERE))
