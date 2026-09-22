// Deterministic UI fixtures only. This test never authenticates to production.
// TRIDENT_PLAYWRIGHT_MODULE can point to an existing local Playwright installation.
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
const { chromium, webkit } = await import(process.env.TRIDENT_PLAYWRIGHT_MODULE || "playwright");
const base = process.env.TRIDENT_TEST_URL || "http://127.0.0.1:4185";
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error("Loopback test origin required");
const output = process.env.TRIDENT_CAPTURE_DIR || "/tmp/trident-master-captures";
await mkdir(output, { recursive: true });
const sizes = [[390,844],[430,932],[768,1024],[1024,768],[1366,768],[1440,900],[1920,1080]];
const workspaces = [{ id:"ws-1", name:"Atelier céleste", description:"Espace de test isolé" }, { id:"ws-2", name:"Second Workspace" }];
const session = { user:{ id:"test-user", display_name:"Test local" }, active_organization_id:"org", active_workspace_id:"ws-1", organizations:[{id:"org",name:"Test",role:"owner",workspaces}] };
const text = "Une réponse **structurée** et lisible.\n\n## Intelligence du Workspace\n\n- Knowledge pour les sources\n- Memory pour les repères\n\n```js\nconst example = '" + "long_".repeat(40) + "';\n```\n\n" + "Une phrase lisible dans un long échange. ".repeat(40);
let assertions = 0;
for (const [name, engine] of [["chromium", chromium], ["webkit", webkit]]) {
  let browser;
  const wk = process.env.TRIDENT_WEBKIT_ROOT;
  const launch = name === "webkit" && wk ? { executablePath: `${wk}/bin/MiniBrowser`, env: { ...process.env, WEBKIT_EXEC_PATH:`${wk}/bin`, WEBKIT_INJECTED_BUNDLE_PATH:`${wk}/lib`, WEBKIT_INSPECTOR_RESOURCES_PATH:`${wk}/share`, LD_LIBRARY_PATH:`${wk}/lib:${wk}/sys/lib:${process.env.LD_LIBRARY_PATH || ""}` } } : {};
  try { browser = await engine.launch({ headless: true, ...launch }); }
  catch (error) { console.log(`${name}: UNAVAILABLE ${error.message.split("\n")[0]}`); continue; }
  try {
    for (const [width,height] of sizes) {
      const context = await browser.newContext({viewport:{width,height},deviceScaleFactor:1,hasTouch:width<761,isMobile:width<761});
      const page = await context.newPage();
      let imageAvailable = false;
      let authenticated = true;
      let imageRecords = [];
      let imagePosts = 0;
      let editBody = "";
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.addInitScript(() => {
        localStorage.setItem("trident.ai.product_onboarding.test-user", "complete");
        localStorage.setItem("trident.ai.active_workspace_id", "ws-1");
      });
      await page.route("**/*", async route => {
        const url = new URL(route.request().url());
        if (url.origin !== base) return route.abort();
        if (!url.pathname.startsWith("/api/")) return route.continue();
        const path = url.pathname;
        let data;
        if (path.endsWith("/session/configuration")) data={enabled:true};
        else if (path.endsWith("/session")) {
          if (!authenticated) return route.fulfill({status:401,contentType:"application/json",body:JSON.stringify({error:{message:"Authentication required"}})});
          data=session;
        }
        else if (path.endsWith("/workspaces")) data=workspaces;
        else if (path.endsWith("/images/capability")) data={available:imageAvailable,reason:imageAvailable ? null : "configuration_required"};
        else if (path.endsWith("/conversations/conv-1/images") && route.request().method() === "POST") {
          imagePosts++; editBody = route.request().postData() || "";
          data={id:`image-${imagePosts}`,message_id:`image-message-${imagePosts}`,conversation_id:"conv-1",workspace_id:"ws-1",prompt:"Ville céleste de test",status:"queued",aspect_ratio:"3:2",can_cancel:true,width:24,height:16};
          imageRecords.push(data);
        }
        else if (path.endsWith("/images")) data=imageRecords;
        else if (path.endsWith("/content")) return route.fulfill({status:200,contentType:"image/png",body:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=","base64")});
        else if (path.endsWith("/conversations")) data=[{id:"conv-1",title:"Penser dans le Workspace",created_at:"2026-09-20T00:00:00Z"}];
        else if (path.endsWith("/conversations/conv-1")) data={id:"conv-1",title:"Penser dans le Workspace",messages:[{id:"m1",role:"user",content:"Explique le contexte du Workspace.",citations:[]},{id:"m2",role:"assistant",content:text,citations:[{document_id:"doc",document_name:"source_".repeat(40)+".pdf"}]},...imageRecords.flatMap(item=>[{id:`user-${item.id}`,role:"user",content:item.prompt,citations:[]},{id:item.message_id,role:"assistant",content:"Création d’image demandée.",citations:[]}])]};
        else if (path.endsWith("/overview")) data={metrics:{documents:0,conversations:1,messages:2,memories:0}};
        else if (/\/(images|activity|memories|documents|modules)$/.test(path)) data=[];
        else if (/\/workspaces\/ws-[12]$/.test(path)) data=workspaces.find(w=>path.endsWith(w.id));
        else return route.fulfill({status:404,contentType:"application/json",body:JSON.stringify({error:{message:"Unmocked test path: "+path}})});
        return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({data,meta:{pagination:{has_more:false}}})});
      });
      await page.goto(base);
      await page.locator(".nova-ready__identity").waitFor();
      await page.locator(".trident-environment__world-art").evaluate(img=>img.decode());
      await page.screenshot({path:`${output}/${name}-landing-${width}x${height}.png`});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,"Landing overflow"); assertions++;
      if (width > 1100) {
        const rail = await page.evaluate(() => ({
          selectorBottom: document.querySelector(".sidebar .workspace-selector").getBoundingClientRect().bottom,
          createTop: document.querySelector(".sidebar-create").getBoundingClientRect().top,
        }));
        assert.ok(rail.createTop >= rail.selectorBottom, "Workspace selector overlaps creation control"); assertions++;
      }
      await page.getByRole("button",{name:"Ouvrir le menu système TRIDENT"}).click();
      await page.locator(".mobile-workspace-sheet__recent button").filter({hasText:"Penser dans le Workspace"}).click();
      await page.locator(".nova-markdown pre").waitFor();
      assert.equal(await page.locator(".mobile-workspace-sheet").count(),0); assertions++;
      const geometry=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,composer:document.querySelector(".message-composer").getBoundingClientRect().bottom,body:innerHeight,scroll:document.querySelector(".message-list").clientHeight}));
      await page.screenshot({path:`${output}/${name}-conversation-${width}x${height}.png`});
      console.log(`${name} ${width}x${height} geometry`, geometry);
      if (geometry.scroll < height*.45) console.log(await page.evaluate(()=>[...document.querySelectorAll('.main-layout,.main-content,.workspace,.workspace-container,.conversation-layout,.conversation-panel,.message-list,.message-composer')].map(el=>({class:el.className,height:el.getBoundingClientRect().height,display:getComputedStyle(el).display,rows:getComputedStyle(el).gridTemplateRows,flex:getComputedStyle(el).flex,min:getComputedStyle(el).minHeight,max:getComputedStyle(el).maxHeight}))));
      assert.equal(geometry.overflow,false,"Conversation overflow");
      assert.ok(geometry.composer<=height+1,"Composer outside viewport");
      assert.ok(geometry.scroll>height*.45,"Insufficient conversation viewport"); assertions+=3;
      await page.locator(".message-list").evaluate(node=>node.scrollTop=node.scrollHeight);
      await page.screenshot({path:`${output}/${name}-conversation-${width}x${height}.png`});
      await page.getByRole("button",{name:"Ouvrir TRIDENT Command"}).click();
      await page.getByRole("textbox",{name:"Rechercher une commande TRIDENT"}).fill("Paramètres");
      await page.locator("[data-command-result]").first().click();
      await page.locator(".settings-card").first().waitFor();
      const blurs=await page.locator(".settings-card").evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).backdropFilter || getComputedStyle(node).webkitBackdropFilter));
      assert.ok(blurs.every(blur=>!blur || blur==="none"),"Settings still use expensive backdrop"); assertions++;
      await page.locator(".workspace").evaluate(node=>node.scrollTop=node.scrollHeight);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true); assertions++;
      await page.screenshot({path:`${output}/${name}-settings-${width}x${height}.png`});
      if (width === 390 || width === 1440) {
        imageAvailable = true;
        await page.getByRole("button",{name:"Ouvrir TRIDENT Command"}).click();
        await page.getByRole("textbox",{name:"Rechercher une commande TRIDENT"}).fill("Nova");
        await page.locator("[data-command-result]").first().click();
        await page.locator(".message-composer__tools button").click();
        await page.getByRole("textbox",{name:"Message à Nova"}).fill("Ville céleste de test");
        await page.getByLabel("Format d’image").selectOption("3:2");
        await page.getByRole("button",{name:"Envoyer le message"}).click();
        await page.locator(".nova-image").first().waitFor();
        assert.equal(imagePosts,1); assertions++;
        assert.match(await page.locator(".nova-image header").first().textContent(),/En attente/); assertions++;
        imageRecords[0]={...imageRecords[0],status:"completed",can_cancel:false};
        await page.getByRole("link",{name:"Télécharger"}).waitFor({timeout:12000});
        await page.getByRole("button",{name:"Modifier",exact:true}).click();
        await page.getByRole("textbox",{name:"Message à Nova"}).fill("Rends le ciel plus sombre");
        await page.getByRole("button",{name:"Envoyer le message"}).click();
        await page.waitForFunction(()=>document.querySelectorAll('.nova-image').length===2);
        assert.equal(imagePosts,2); assert.match(editBody,/source_id/); assert.match(editBody,/image-1/); assertions+=3;
        await page.screenshot({path:`${output}/${name}-images-${width}x${height}.png`});
        for (const label of ["Knowledge", "Memory", "Fichiers", "Artefacts", "Activité", "Accueil"]) {
          await page.getByRole("button",{name:"Ouvrir TRIDENT Command"}).click();
          await page.getByRole("textbox",{name:"Rechercher une commande TRIDENT"}).fill(label);
          await page.locator("[data-command-result]").first().click();
          await page.locator(".workspace :is(.product-view,.knowledge-view,.memory-view,.workspace-home)").first().waitFor();
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${label} overflow`); assertions++;
          await page.screenshot({path:`${output}/${name}-${label}-${width}x${height}.png`});
        }
        authenticated=false;
        await page.reload();
        await page.getByRole("button",{name:"Se connecter",exact:true}).waitFor();
        assert.match(await page.locator(".entry-attribution").textContent(),/Created by Salmane Hassan/);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true); assertions+=2;
        await page.screenshot({path:`${output}/${name}-auth-${width}x${height}.png`});
      }
      assert.deepEqual(errors,[]); assertions++;
      console.log(`${name} ${width}x${height}: PASS`);
      await context.close();
    }
  } finally { await browser.close(); }
}
if (!assertions) throw new Error("No browser executed: browser gate unavailable");
console.log(`Browser assertions: ${assertions} PASS (fixtures; no FPS claim)`);
