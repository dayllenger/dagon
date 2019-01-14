﻿/*
Copyright (c) 2019 dayllenger

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

module dagon.graphics.shaderloader;

import std.stdio;
import std.string : stripRight;
import dlib.math.utils : min2;
import dagon.core.libs;

enum ShaderStage : ubyte
{
    vertex = 1,
    tessControl = 2,
    tessEval = 4,
    geometry = 8,
    fragment = 16,
    compute = 32
}

private GLenum shaderStageToGLenum(ShaderStage stage)
{
    final switch (stage) with(ShaderStage)
    {
        case vertex:      return GL_VERTEX_SHADER;
        case tessControl: return GL_TESS_CONTROL_SHADER;
        case tessEval:    return GL_TESS_EVALUATION_SHADER;
        case geometry:    return GL_GEOMETRY_SHADER;
        case fragment:    return GL_FRAGMENT_SHADER;
    static if (glSupport >= GLSupport.gl43)
        case compute:     return GL_COMPUTE_SHADER;
    else
        case compute:     return 0;
    }
}

/// Compile single shader from source
GLuint compileShader(string source, const ShaderStage stage)
{
    // create a shader
    GLuint shaderID = glCreateShader(shaderStageToGLenum(stage));

    // compile the shader
    const char* csource = source.ptr;
    GLint length = cast(GLint)source.length;
    glShaderSource(shaderID, 1, &csource, &length);
    glCompileShader(shaderID);

    // check the shader
    if (!checkCompilation(shaderID, stage))
    {
        shaderID = 0;
        glDeleteShader(shaderID);
    }

    return shaderID;
}

/// Link compiled shaders
GLuint linkShaders(const GLuint[] shaderIDs...)
{
    // create and link program
    GLuint programID = glCreateProgram();
    foreach(sh; shaderIDs)
        glAttachShader(programID, sh);
    glLinkProgram(programID);

    // check the program
    if (!checkLinking(programID))
    {
        programID = 0;
        glDeleteProgram(programID);
    }

    // delete the program parts
    foreach(sh; shaderIDs)
    {
        glDetachShader(programID, sh);
        glDeleteShader(sh);
    }

    return programID;
}

private enum logMaxLen = 1023;

private bool checkCompilation(const GLuint shaderID, const ShaderStage stage)
{
    // get status
    GLint status = GL_FALSE;
    glGetShaderiv(shaderID, GL_COMPILE_STATUS, &status);
    const bool ok = status != GL_FALSE;
    // get log
    GLint infolen;
    glGetShaderiv(shaderID, GL_INFO_LOG_LENGTH, &infolen); // includes \0
    if (infolen > 1)
    {
        char[logMaxLen + 1] infobuffer = 0;
        glGetShaderInfoLog(shaderID, logMaxLen, null, infobuffer.ptr);
        infolen = min2(infolen - 1, logMaxLen);
        char[] s = stripRight(infobuffer[0 .. infolen]);
        // it can be some warning
        if (!ok)
            writefln("Failed to compile %s shader:", stage);
        writeln(s);
    }
    return ok;
}

private bool checkLinking(const GLuint programID)
{
    // get status
    GLint status = GL_FALSE;
    glGetProgramiv(programID, GL_LINK_STATUS, &status);
    const bool ok = status != GL_FALSE;
    // get log
    GLint infolen;
    glGetProgramiv(programID, GL_INFO_LOG_LENGTH, &infolen); // includes \0
    if (infolen > 1)
    {
        char[logMaxLen + 1] infobuffer = 0;
        glGetProgramInfoLog(programID, logMaxLen, null, infobuffer.ptr);
        infolen = min2(infolen - 1, logMaxLen);
        char[] s = stripRight(infobuffer[0 .. infolen]);
        // it can be some warning
        if (!ok)
            writeln("Failed to link shaders:");
        writeln(s);
    }
    return ok;
}
