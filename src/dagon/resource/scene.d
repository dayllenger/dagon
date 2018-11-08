/*
Copyright (c) 2017-2018 Timur Gafarov

Boost Software License - Version 1.0 - August 17th, 2003
Permission is hereby granted, free of charge, to any person or organization
obtaining a copy of the software and accompanying documentation covered by
this license (the "Software") to use, reproduce, display, distribute,
execute, and transmit the Software, and to prepare derivative works of the
Software, and to permit third-parties to whom the Software is furnished to
do so, all subject to the following:

The copyright notices in the Software and this entire statement, including
the above license grant, this restriction and the following disclaimer,
must be included in all copies of the Software, in whole or in part, and
all derivative works of the Software, unless such copies or derivative
works are solely in the form of machine-executable object code generated by
a source language processor.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
*/

module dagon.resource.scene;

import std.stdio;
import std.math;
import std.algorithm;
import std.traits;

import dlib.core.memory;

import dlib.container.array;
import dlib.container.dict;
import dlib.math.vector;
import dlib.math.matrix;
import dlib.math.transformation;
import dlib.image.color;
import dlib.image.image;
import dlib.image.unmanaged;
import dlib.image.io.png;

import dagon.core.libs;
import dagon.core.ownership;
import dagon.core.event;
import dagon.core.application;
import dagon.resource.asset;
import dagon.resource.textasset;
import dagon.resource.textureasset;
import dagon.resource.fontasset;
import dagon.resource.obj;
import dagon.resource.iqm;
import dagon.resource.packageasset;
import dagon.graphics.environment;
import dagon.graphics.rc;
import dagon.graphics.view;
import dagon.graphics.shapes;
import dagon.graphics.light;
import dagon.graphics.probe;
import dagon.graphics.shadow;
import dagon.graphics.texture;
import dagon.graphics.particles;
import dagon.graphics.materials.generic;
import dagon.graphics.materials.standard;
import dagon.graphics.materials.hud;
import dagon.graphics.materials.particle;
import dagon.graphics.framebuffer;
import dagon.graphics.shader;
import dagon.graphics.shaders.standard;
import dagon.graphics.shaders.sky;
import dagon.graphics.shaders.particle;
import dagon.graphics.renderer;
import dagon.graphics.postproc;
import dagon.graphics.filters.fxaa;
import dagon.graphics.filters.lens;
import dagon.graphics.filters.hdrprepass;
import dagon.graphics.filters.hdr;
import dagon.graphics.filters.blur;
import dagon.graphics.filters.finalizer;
import dagon.logics.entity;

class BaseScene: EventListener
{
    SceneManager sceneManager;
    AssetManager assetManager;
    bool canRun = false;
    bool releaseAtNextStep = false;
    bool needToLoad = true;

    this(SceneManager smngr)
    {
        super(smngr.eventManager, null);
        sceneManager = smngr;
        assetManager = New!AssetManager(eventManager);
    }

    ~this()
    {
        release();
        Delete(assetManager);
    }

    // Set preload to true if you want to load the asset immediately
    // before actual loading (e.g., to render a loading screen)
    Asset addAsset(Asset asset, string filename, bool preload = false)
    {
        if (preload)
            assetManager.preloadAsset(asset, filename);
        else
            assetManager.addAsset(asset, filename);
        return asset;
    }

    void onAssetsRequest()
    {
        // Add your assets here
    }

    void onLoading(float percentage)
    {
        // Render your loading screen here
    }

    void onAllocate()
    {
        // Allocate your objects here
    }

    void onRelease()
    {
        // Release your objects here
    }

    void onStart()
    {
        // Do your (re)initialization here
    }

    void onEnd()
    {
        // Do your finalization here
    }

    void onUpdate(double dt)
    {
        // Do your animation and logics here
    }

    void onRender()
    {
        // Do your rendering here
    }

    void exitApplication()
    {
        generateUserEvent(DagonEvent.Exit);
    }

    void load()
    {
        if (needToLoad)
        {
            onAssetsRequest();
            float p = assetManager.nextLoadingPercentage;

            assetManager.loadThreadSafePart();

            while(assetManager.isLoading)
            {
                sceneManager.application.beginRender();
                onLoading(p);
                sceneManager.application.endRender();
                p = assetManager.nextLoadingPercentage;
            }

            bool loaded = assetManager.loadThreadUnsafePart();

            if (loaded)
            {
                onAllocate();
                canRun = true;
                needToLoad = false;
            }
            else
            {
                writeln("Exiting due to error while loading assets");
                canRun = false;
                eventManager.running = false;
            }
        }
        else
        {
            canRun = true;
        }
    }

    void release()
    {
        onRelease();
        clearOwnedObjects();
        assetManager.releaseAssets();
        needToLoad = true;
        canRun = false;
    }

    void start()
    {
        if (canRun)
            onStart();
    }

    void end()
    {
        if (canRun)
            onEnd();
    }

    void update(double dt)
    {
        if (canRun)
        {
            processEvents();
            assetManager.updateMonitor(dt);
            onUpdate(dt);
        }

        if (releaseAtNextStep)
        {
            end();
            release();

            releaseAtNextStep = false;
            canRun = false;
        }
    }

    void render()
    {
        if (canRun)
            onRender();
    }
}

class SceneManager: Owner
{
    SceneApplication application;
    Dict!(BaseScene, string) scenesByName;
    EventManager eventManager;
    BaseScene currentScene;

    this(EventManager emngr, SceneApplication app)
    {
        super(app);
        application = app;
        eventManager = emngr;
        scenesByName = New!(Dict!(BaseScene, string));
    }

    ~this()
    {
        foreach(i, s; scenesByName)
        {
            Delete(s);
        }
        Delete(scenesByName);
    }

    BaseScene addScene(BaseScene scene, string name)
    {
        scenesByName[name] = scene;
        return scene;
    }

    void removeScene(string name)
    {
        Delete(scenesByName[name]);
        scenesByName.remove(name);
    }

    void goToScene(string name, bool releaseCurrent = true)
    {
        if (currentScene && releaseCurrent)
        {
            currentScene.releaseAtNextStep = true;
        }

        BaseScene scene = scenesByName[name];

        writefln("Loading scene \"%s\"", name);

        scene.load();
        currentScene = scene;
        currentScene.start();

        writefln("Running...", name);
    }

    void update(double dt)
    {
        if (currentScene)
        {
            currentScene.update(dt);
        }
    }

    void render()
    {
        if (currentScene)
        {
            currentScene.render();
        }
    }
}

class SceneApplication: Application
{
    SceneManager sceneManager;
    UnmanagedImageFactory imageFactory;
    SuperImage screenshotBuffer1;
    SuperImage screenshotBuffer2;

    this(uint w, uint h, bool fullscreen, string windowTitle, string[] args)
    {
        super(w, h, fullscreen, windowTitle, args);

        sceneManager = New!SceneManager(eventManager, this);

        imageFactory = New!UnmanagedImageFactory();
        screenshotBuffer1 = imageFactory.createImage(eventManager.windowWidth, eventManager.windowHeight, 3, 8);
        screenshotBuffer2 = imageFactory.createImage(eventManager.windowWidth, eventManager.windowHeight, 3, 8);
    }

    ~this()
    {
        Delete(imageFactory);
        Delete(screenshotBuffer1);
        Delete(screenshotBuffer2);
    }

    override void onUpdate(double dt)
    {
        sceneManager.update(dt);
    }

    override void onRender()
    {
        sceneManager.render();
    }

    void saveScreenshot(string filename)
    {
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glReadPixels(0, 0, eventManager.windowWidth, eventManager.windowHeight, GL_RGB, GL_UNSIGNED_BYTE, screenshotBuffer1.data.ptr);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 4);

        foreach(y; 0..screenshotBuffer1.height)
        foreach(x; 0..screenshotBuffer1.width)
        {
            screenshotBuffer2[x, y] = screenshotBuffer1[x, screenshotBuffer1.height - y];
        }

        screenshotBuffer2.savePNG(filename);
    }
}

// TODO: Renderer class
class Scene: BaseScene
{
    Renderer renderer;
    EnvironmentProbeRenderTarget eprt;
    
    Environment environment;

    LightManager lightManager;
    ParticleSystem particleSystem;

	StandardShader standardShader;
    SkyShader skyShader;
    ParticleShader particleShader;
    GenericMaterial defaultMaterial3D;

    StandardBackend defaultMaterialBackend;

    RenderingContext rc3d;
    RenderingContext rc2d;
    View view;

    PostFilterHDR hdrFilter;

    Framebuffer hdrPrepassFramebuffer;
    PostFilterHDRPrepass hdrPrepassFilter;

    Framebuffer hblurredFramebuffer;
    Framebuffer vblurredFramebuffer;
    PostFilterBlur hblur;
    PostFilterBlur vblur;

    PostFilterFXAA fxaaFilter;
    PostFilterLensDistortion lensFilter;

    PostFilterFinalizer finalizerFilter;

	//TODO: move post-processing to a separate class
    struct SSAOSettings
    {
        BaseScene3D scene;

        void enabled(bool mode) @property
        {
            scene.renderer.deferredEnvPass.shader.enableSSAO = mode;
        }

        bool enabled() @property
        {
            return scene.renderer.deferredEnvPass.shader.enableSSAO;
        }
        
        void samples(int s) @property
        {
            scene.renderer.deferredEnvPass.shader.ssaoSamples = s;
        }

        int samples() @property
        {
            return scene.renderer.deferredEnvPass.shader.ssaoSamples;
        }
        
        void radius(float r) @property
        {
            scene.renderer.deferredEnvPass.shader.ssaoRadius = r;
        }

        float radius() @property
        {
            return scene.renderer.deferredEnvPass.shader.ssaoRadius;
        }
        
        void power(float p) @property
        {
            scene.renderer.deferredEnvPass.shader.ssaoPower = p;
        }

        float power() @property
        {
            return scene.renderer.deferredEnvPass.shader.ssaoPower;
        }

        //TODO: other SSAO parameters
    }

    struct HDRSettings
    {
        BaseScene3D scene;

        void tonemapper(Tonemapper f) @property
        {
            scene.hdrFilter.tonemapFunction = f;
        }

        Tonemapper tonemapper() @property
        {
            return scene.hdrFilter.tonemapFunction;
        }


        void exposure(float ex) @property
        {
            scene.hdrFilter.exposure = ex;
        }

        float exposure() @property
        {
            return scene.hdrFilter.exposure;
        }


        void autoExposure(bool mode) @property
        {
            scene.hdrFilter.autoExposure = mode;
        }

        bool autoExposure() @property
        {
            return scene.hdrFilter.autoExposure;
        }


        void minLuminance(float l) @property
        {
            scene.hdrFilter.minLuminance = l;
        }

        float minLuminance() @property
        {
            return scene.hdrFilter.minLuminance;
        }


        void maxLuminance(float l) @property
        {
            scene.hdrFilter.maxLuminance = l;
        }

        float maxLuminance() @property
        {
            return scene.hdrFilter.maxLuminance;
        }


        void keyValue(float k) @property
        {
            scene.hdrFilter.keyValue = k;
        }

        float keyValue() @property
        {
            return scene.hdrFilter.keyValue;
        }


        void adaptationSpeed(float s) @property
        {
            scene.hdrFilter.adaptationSpeed = s;
        }

        float adaptationSpeed() @property
        {
            return scene.hdrFilter.adaptationSpeed;
        }
    }

    struct GlowSettings
    {
        BaseScene3D scene;
        uint radius;

        void enabled(bool mode) @property
        {
            scene.hblur.enabled = mode;
            scene.vblur.enabled = mode;
            scene.hdrPrepassFilter.glowEnabled = mode;
        }

        bool enabled() @property
        {
            return scene.hdrPrepassFilter.glowEnabled;
        }


        void brightness(float b) @property
        {
            scene.hdrPrepassFilter.glowBrightness = b;
        }

        float brightness() @property
        {
            return scene.hdrPrepassFilter.glowBrightness;
        }
    }

    struct MotionBlurSettings
    {
        BaseScene3D scene;

        void enabled(bool mode) @property
        {
            scene.hdrFilter.mblurEnabled = mode;
        }

        bool enabled() @property
        {
            return scene.hdrFilter.mblurEnabled;
        }


        void samples(uint s) @property
        {
            scene.hdrFilter.motionBlurSamples = s;
        }

        uint samples() @property
        {
            return scene.hdrFilter.motionBlurSamples;
        }


        void shutterSpeed(float s) @property
        {
            scene.hdrFilter.shutterSpeed = s;
            scene.hdrFilter.shutterFps = 1.0 / s;
        }

        float shutterSpeed() @property
        {
            return scene.hdrFilter.shutterSpeed;
        }
    }

    struct LUTSettings
    {
        BaseScene3D scene;

        void texture(Texture tex) @property
        {
            scene.hdrFilter.colorTable = tex;
        }

        Texture texture() @property
        {
            return scene.hdrFilter.colorTable;
        }
    }

    struct VignetteSettings
    {
        BaseScene3D scene;

        void texture(Texture tex) @property
        {
            scene.hdrFilter.vignette = tex;
        }

        Texture texture() @property
        {
            return scene.hdrFilter.vignette;
        }
    }

    struct AASettings
    {
        BaseScene3D scene;

        void enabled(bool mode) @property
        {
            scene.fxaaFilter.enabled = mode;
        }

        bool enabled() @property
        {
            return scene.fxaaFilter.enabled;
        }
    }

    struct LensSettings
    {
        BaseScene3D scene;

        void enabled(bool mode) @property
        {
            scene.lensFilter.enabled = mode;
        }

        bool enabled() @property
        {
            return scene.lensFilter.enabled;
        }

        void scale(float s) @property
        {
            scene.lensFilter.scale = s;
        }

        float scale() @property
        {
            return scene.lensFilter.scale;
        }


        void dispersion(float d) @property
        {
            scene.lensFilter.dispersion = d;
        }

        float dispersion() @property
        {
            return scene.lensFilter.dispersion;
        }
    }

    SSAOSettings ssao;
    HDRSettings hdr;
    MotionBlurSettings motionBlur;
    GlowSettings glow;
    LUTSettings lut;
    VignetteSettings vignette;
    AASettings antiAliasing;
    LensSettings lensDistortion;

    DynamicArray!PostFilter postFilters;

    DynamicArray!Entity entities3D;
    DynamicArray!Entity entities2D;

    ShapeQuad loadingProgressBar;
    Entity eLoadingProgressBar;
    HUDMaterialBackend hudMaterialBackend;
    GenericMaterial mLoadingProgressBar;

    double timer = 0.0;
    double fixedTimeStep = 1.0 / 60.0;

    this(SceneManager smngr)
    {
        super(smngr);

        rc3d.init(eventManager, environment);
        rc3d.projectionMatrix = perspectiveMatrix(60.0f, eventManager.aspectRatio, 0.1f, 1000.0f);

        rc2d.init(eventManager, environment);
        rc2d.projectionMatrix = orthoMatrix(0.0f, eventManager.windowWidth, 0.0f, eventManager.windowHeight, 0.0f, 100.0f);

        loadingProgressBar = New!ShapeQuad(assetManager);
        eLoadingProgressBar = New!Entity(eventManager, assetManager);
        eLoadingProgressBar.drawable = loadingProgressBar;
        hudMaterialBackend = New!HUDMaterialBackend(assetManager);
        mLoadingProgressBar = createGenericMaterial(hudMaterialBackend);
        mLoadingProgressBar.diffuse = Color4f(1, 1, 1, 1);
        eLoadingProgressBar.material = mLoadingProgressBar;
    }

    void sortEntities(ref DynamicArray!Entity entities)
    {
        size_t j = 0;
        Entity tmp;

        auto edata = entities.data;

        foreach(i, v; edata)
        {
            j = i;
            size_t k = i;

            while (k < edata.length)
            {
                float b1 = edata[j].layer;
                float b2 = edata[k].layer;

                if (b2 < b1)
                    j = k;

                k++;
            }

            tmp = edata[i];
            edata[i] = edata[j];
            edata[j] = tmp;

            sortEntities(v.children);
        }
    }

    TextAsset addTextAsset(string filename, bool preload = false)
    {
        TextAsset text;
        if (assetManager.assetExists(filename))
            text = cast(TextAsset)assetManager.getAsset(filename);
        else
        {
            text = New!TextAsset(assetManager);
            addAsset(text, filename, preload);
        }
        return text;
    }

    TextureAsset addTextureAsset(string filename, bool preload = false)
    {
        TextureAsset tex;
        if (assetManager.assetExists(filename))
            tex = cast(TextureAsset)assetManager.getAsset(filename);
        else
        {
            tex = New!TextureAsset(assetManager.imageFactory, assetManager.hdrImageFactory, assetManager);
            addAsset(tex, filename, preload);
        }
        return tex;
    }

    FontAsset addFontAsset(string filename, uint height, bool preload = false)
    {
        FontAsset font;
        if (assetManager.assetExists(filename))
            font = cast(FontAsset)assetManager.getAsset(filename);
        else
        {
            font = New!FontAsset(height, assetManager);
            addAsset(font, filename, preload);
        }
        return font;
    }

    OBJAsset addOBJAsset(string filename, bool preload = false)
    {
        OBJAsset obj;
        if (assetManager.assetExists(filename))
            obj = cast(OBJAsset)assetManager.getAsset(filename);
        else
        {
            obj = New!OBJAsset(assetManager);
            addAsset(obj, filename, preload);
        }
        return obj;
    }

    IQMAsset addIQMAsset(string filename, bool preload = false)
    {
        IQMAsset iqm;
        if (assetManager.assetExists(filename))
            iqm = cast(IQMAsset)assetManager.getAsset(filename);
        else
        {
            iqm = New!IQMAsset(assetManager);
            addAsset(iqm, filename, preload);
        }
        return iqm;
    }

    PackageAsset addPackageAsset(string filename, bool preload = false)
    {
        PackageAsset pa;
        if (assetManager.assetExists(filename))
            pa = cast(PackageAsset)assetManager.getAsset(filename);
        else
        {
            pa = New!PackageAsset(this, assetManager);
            addAsset(pa, filename, preload);
        }
        return pa;
    }

    Entity createEntity2D(Entity parent = null)
    {
        Entity e;
        if (parent)
            e = New!Entity(parent);
        else
        {
            e = New!Entity(eventManager, assetManager);
            entities2D.append(e);

            sortEntities(entities2D);
        }

        return e;
    }

    Entity createEntity3D(Entity parent = null)
    {
        Entity e;
        if (parent)
            e = New!Entity(parent);
        else
        {
            e = New!Entity(eventManager, assetManager);
            entities3D.append(e);

            sortEntities(entities3D);
        }

        e.material = defaultMaterial3D;

        return e;
    }

    Entity addEntity3D(Entity e)
    {
        entities3D.append(e);
        sortEntities(entities3D);
        return e;
    }

    Entity createSky(GenericMaterial mat = null)
    {
        GenericMaterial matSky;
        if (mat is null)
        {
            matSky = New!ShaderMaterial(skyShader, assetManager);
            matSky.depthWrite = false;
        }
        else
        {
            matSky = mat;
        }

        auto eSky = createEntity3D();
        eSky.layer = 0;
        eSky.attach = Attach.Camera;
        eSky.castShadow = false;
        eSky.material = matSky;
        // TODO: use box instead of sphere
        eSky.drawable = New!ShapeSphere(1.0f, 16, 8, true, assetManager);
        eSky.scaling = Vector3f(100.0f, 100.0f, 100.0f);
        sortEntities(entities3D);
        return eSky;
    }

    ShaderMaterial createMaterial(Shader shader)
    {
        auto m = New!ShaderMaterial(shader, assetManager);
        if (shader !is standardShader)
            m.customShader = true;
        return m;
    }

    ShaderMaterial createMaterial()
    {
        return createMaterial(standardShader);
    }

	// TODO: replace with ShaderMaterial
    deprecated GenericMaterial createGenericMaterial(GenericMaterialBackend backend = null)
    {
        if (backend is null)
            backend = defaultMaterialBackend;
        return New!GenericMaterial(backend, assetManager);
    }

    GenericMaterial createParticleMaterial(Shader shader = null)
    {
        if (shader is null)
            shader = particleShader;
        return New!ShaderMaterial(shader, assetManager);
    }

    LightSource createLight(Vector3f position, Color4f color, float energy, float volumeRadius, float areaRadius = 0.0f)
    {
        return lightManager.addLight(position, color, energy, volumeRadius, areaRadius);
    }

    override void onAllocate()
    {
        environment = New!Environment(assetManager);
        lightManager = New!LightManager(assetManager);
        
        renderer = New!Renderer(this, assetManager);
        eprt = New!EnvironmentProbeRenderTarget(128, assetManager);

        defaultMaterialBackend = New!StandardBackend(lightManager, assetManager);

		standardShader = New!StandardShader(assetManager);
        standardShader.shadowMap = renderer.shadowMap;
        skyShader = New!SkyShader(assetManager);
        particleShader = New!ParticleShader(renderer.gbuffer, assetManager);

        defaultMaterialBackend.shadowMap = renderer.shadowMap;

        particleSystem = New!ParticleSystem(assetManager);

        defaultMaterial3D = createMaterial();

        ssao.scene = this;
        hdr.scene = this;
        motionBlur.scene = this;
        glow.scene = this;
        glow.radius = 3;
        lut.scene = this;
        vignette.scene = this;
        antiAliasing.scene = this;
        lensDistortion.scene = this;

        hblurredFramebuffer = New!Framebuffer(renderer.gbuffer, eventManager.windowWidth / 2, eventManager.windowHeight / 2, true, false, assetManager);
        hblur = New!PostFilterBlur(true, renderer.sceneFramebuffer, hblurredFramebuffer, assetManager);

        vblurredFramebuffer = New!Framebuffer(renderer.gbuffer, eventManager.windowWidth / 2, eventManager.windowHeight / 2, true, false, assetManager);
        vblur = New!PostFilterBlur(false, hblurredFramebuffer, vblurredFramebuffer, assetManager);

        hdrPrepassFramebuffer = New!Framebuffer(renderer.gbuffer, eventManager.windowWidth, eventManager.windowHeight, true, false, assetManager);
        hdrPrepassFilter = New!PostFilterHDRPrepass(renderer.sceneFramebuffer, hdrPrepassFramebuffer, assetManager);
        hdrPrepassFilter.blurredTexture = vblurredFramebuffer.currentColorTexture;
        postFilters.append(hdrPrepassFilter);

        hdrFilter = New!PostFilterHDR(hdrPrepassFramebuffer, null, assetManager);
        hdrFilter.velocityTexture = renderer.gbuffer.velocityTexture;
        postFilters.append(hdrFilter);

        fxaaFilter = New!PostFilterFXAA(null, null, assetManager);
        postFilters.append(fxaaFilter);
        fxaaFilter.enabled = false;

        lensFilter = New!PostFilterLensDistortion(null, null, assetManager);
        postFilters.append(lensFilter);
        lensFilter.enabled = false;

        finalizerFilter = New!PostFilterFinalizer(null, null, assetManager);
    }

    PostFilter addFilter(PostFilter f)
    {
        postFilters.append(f);
        return f;
    }

    override void onRelease()
    {
        entities3D.free();
        entities2D.free();

        postFilters.free();
    }

    override void onLoading(float percentage)
    {
        glEnable(GL_SCISSOR_TEST);
        glScissor(0, 0, eventManager.windowWidth, eventManager.windowHeight);
        glViewport(0, 0, eventManager.windowWidth, eventManager.windowHeight);
        glClearColor(0, 0, 0, 1);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        float maxWidth = eventManager.windowWidth * 0.33f;
        float x = (eventManager.windowWidth - maxWidth) * 0.5f;
        float y = eventManager.windowHeight * 0.5f - 10;
        float w = percentage * maxWidth;

        glDisable(GL_DEPTH_TEST);
        mLoadingProgressBar.diffuse = Color4f(0.1, 0.1, 0.1, 1);
        eLoadingProgressBar.position = Vector3f(x, y, 0);
        eLoadingProgressBar.scaling = Vector3f(maxWidth, 10, 1);
        eLoadingProgressBar.update(1.0/60.0);
        eLoadingProgressBar.render(&rc2d);

        mLoadingProgressBar.diffuse = Color4f(1, 1, 1, 1);
        eLoadingProgressBar.scaling = Vector3f(w, 10, 1);
        eLoadingProgressBar.update(1.0/60.0);
        eLoadingProgressBar.render(&rc2d);
    }

    override void onStart()
    {
        rc3d.initPerspective(eventManager, environment, 60.0f, 0.1f, 1000.0f);
        rc2d.initOrtho(eventManager, environment, 0.0f, 100.0f);

        timer = 0.0;
    }

    void onLogicsUpdate(double dt)
    {
    }

    override void onUpdate(double dt)
    {
        foreach(e; entities3D)
            e.processEvents();

        foreach(e; entities2D)
            e.processEvents();

        timer += dt;
        if (timer >= fixedTimeStep)
        {
            timer -= fixedTimeStep;

            if (view)
            {
                view.update(fixedTimeStep);
                view.prepareRC(&rc3d);
            }

            rc3d.time += fixedTimeStep;
            rc2d.time += fixedTimeStep;

            foreach(e; entities3D)
                e.update(fixedTimeStep);

            foreach(e; entities2D)
                e.update(fixedTimeStep);

            particleSystem.update(fixedTimeStep);

            onLogicsUpdate(fixedTimeStep);

            environment.update(fixedTimeStep);

            if (view) // TODO: allow to turn this off
            {
                Vector3f cameraDirection = -view.invViewMatrix.forward;
                cameraDirection.y = 0.0f;
                cameraDirection = cameraDirection.normalized;

                renderer.shadowMap.area1.position = view.cameraPosition + cameraDirection * (renderer.shadowMap.projSize1  * 0.5f - 1.0f);
                renderer.shadowMap.area2.position = view.cameraPosition + cameraDirection * renderer.shadowMap.projSize2 * 0.5f;
                renderer.shadowMap.area3.position = view.cameraPosition + cameraDirection * renderer.shadowMap.projSize3 * 0.5f;
            }

            renderer.shadowMap.update(&rc3d, fixedTimeStep);
        }
    }

    void renderBackgroundEntities3D(RenderingContext* rc)
    {
        glEnable(GL_DEPTH_TEST);
        foreach(e; entities3D)
            if (e.layer <= 0)
                e.render(rc);
    }

    // TODO: check transparency of children (use context variable)
    void renderOpaqueEntities3D(RenderingContext* rc)
    {
        glEnable(GL_DEPTH_TEST);
        RenderingContext rcLocal = *rc;
        rcLocal.ignoreTransparentEntities = true;
        foreach(e; entities3D)
        {
            if (e.layer > 0)
                e.render(&rcLocal);
        }
    }

    // TODO: check transparency of children (use context variable)
    void renderTransparentEntities3D(RenderingContext* rc)
    {
        glEnable(GL_DEPTH_TEST);
        RenderingContext rcLocal = *rc;
        rcLocal.ignoreOpaqueEntities = true;
        foreach(e; entities3D)
        {
            if (e.layer > 0)
                e.render(&rcLocal);
        }
    }

    void renderEntities3D(RenderingContext* rc)
    {
        glEnable(GL_DEPTH_TEST);
        foreach(e; entities3D)
            e.render(rc);
    }

    void renderEntities2D(RenderingContext* rc)
    {
        glDisable(GL_DEPTH_TEST);
        foreach(e; entities2D)
            e.render(rc);
    }

    void renderBlur(uint iterations)
    {
        RenderingContext rcTmp;

        foreach(i; 1..iterations+1)
        {
            hblur.outputBuffer.bind();
            rcTmp.initOrtho(eventManager, environment, hblur.outputBuffer.width, hblur.outputBuffer.height, 0.0f, 100.0f);
            renderer.prepareViewport(hblur.outputBuffer);
            hblur.radius = i;
            hblur.render(&rcTmp);
            hblur.outputBuffer.unbind();

            vblur.outputBuffer.bind();
            rcTmp.initOrtho(eventManager, environment, vblur.outputBuffer.width, vblur.outputBuffer.height, 0.0f, 100.0f);
            renderer.prepareViewport(vblur.outputBuffer);
            vblur.radius = i;
            vblur.render(&rcTmp);
            vblur.outputBuffer.unbind();

            hblur.inputBuffer = vblur.outputBuffer;
        }

        hblur.inputBuffer = renderer.sceneFramebuffer;
    }
    
    void renderProbe(EnvironmentProbe probe)
    {
        onUpdate(0.0);
        foreach(face; EnumMembers!CubeFace)
        {
            RenderingContext rcProbe;
            rcProbe.initPerspective(eventManager, environment, 90.0f, 0.1f, 1000.0f);
            eprt.prepareRC(probe, face, &rcProbe);
            eprt.setProbe(probe, face);
            renderer.renderPreStep(eprt.gbuffer, &rcProbe);
            renderer.renderToTarget(eprt, eprt.gbuffer, &rcProbe);
        }
    }

    override void onRender()
    {
        renderer.render(&rc3d);

        if (hdrFilter.autoExposure)
        {
            renderer.sceneFramebuffer.genLuminanceMipmaps();
            float lum = renderer.sceneFramebuffer.averageLuminance();

            if (!isNaN(lum))
            {
                float newExposure = hdrFilter.keyValue * (1.0f / clamp(lum, hdrFilter.minLuminance, hdrFilter.maxLuminance));

                float exposureDelta = newExposure - hdrFilter.exposure;
                hdrFilter.exposure += exposureDelta * hdrFilter.adaptationSpeed * eventManager.deltaTime;
            }
        }

        if (hdrPrepassFilter.glowEnabled)
            renderBlur(glow.radius);

        RenderingContext rcTmp;
        Framebuffer nextInput = renderer.sceneFramebuffer;

        hdrPrepassFilter.perspectiveMatrix = rc3d.projectionMatrix;

        foreach(i, f; postFilters.data)
        if (f.enabled)
        {
            if (f.outputBuffer is null)
                f.outputBuffer = New!Framebuffer(renderer.gbuffer, eventManager.windowWidth, eventManager.windowHeight, false, false, assetManager);

            if (f.inputBuffer is null)
                f.inputBuffer = nextInput;

            nextInput = f.outputBuffer;

            f.outputBuffer.bind();
            rcTmp.initOrtho(eventManager, environment, f.outputBuffer.width, f.outputBuffer.height, 0.0f, 100.0f);
            renderer.prepareViewport(f.outputBuffer);
            f.render(&rcTmp);
            f.outputBuffer.unbind();
        }

        renderer.prepareViewport();
        finalizerFilter.inputBuffer = nextInput;
        finalizerFilter.render(&rc2d);

        renderEntities2D(&rc2d);
    }
}

alias Scene BaseScene3D;
