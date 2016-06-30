# LuaCWC-LuaAutoComplete

A SublimeText plugin which auto completes lua code implements Lua object-oriented.

You should add the function below to define a class defined function:

	function class(classname, super)
	    local superType = type(super)
	    local cls
	
	    if superType ~= "function" and superType ~= "table" then
	        superType = nil
	        super = nil
	    end
	
	    if superType == "function" or (super and super.__ctype == 1) then
	        -- inherited from native C++ Object
	        cls = {}
	
	        if superType == "table" then
	            -- copy fields from super
	            for k,v in pairs(super) do cls[k] = v end
	            cls.__create = super.__create
	            cls.super    = super
	        else
	            cls.__create = super
	        end
	
	        cls.ctor    = function() end
	        cls.__cname = classname
	        cls.__ctype = 1
	
	        function cls.New(...)
	            local instance = cls.__create(...)
	            -- copy fields from class to native object
	            for k,v in pairs(cls) do instance[k] = v end
	            instance.class = cls
	            if instance.ctor then
	                instance:ctor(...)
	            end
	            return instance
	        end
	
	    else
	        -- inherited from Lua Object
	        if super then
	            cls = clone(super)
	            cls.super = super
	        else
	            cls = {ctor = function() end}
	        end
	
	        cls.__cname = classname
	        cls.__ctype = 2 -- lua
	        cls.__index = cls
	
	        function cls.New(...)
	            local instance = setmetatable({}, cls)
	            instance.class = cls
	            if instance.ctor then
	                instance:ctor(...)
	            end
	            return instance
	        end
	    end
	
	    return cls
	end

Then you can define a class:

	ClassName = class("ClassName",
	{
		property1 = nil,
		property2 = nil,
	})


Now instances the object:
'local obj = ClassName.New()'

If you types "obj.", this plugin will find the corresponding class and show its members (property1, property2).




Sometime plugin cannot identify the class of the object because of intricate parameter passing.There are some syntax to solve this problem.

	local obj = parameter --[type:ClassName]
types "obj." you can see the list of completion at the sublime text editor cantain its members.

	function ClassOther:ClassFunc() --[return:ClassName]
		return something
	end
	
	local classOther = ClassOther.New()
	local className = classOther:ClassFunc()
types "className." you can see the list of ClassName members too because ClassOther:ClassFunc() defines ClassName as return Class.
